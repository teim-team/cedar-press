#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Cedar Press - official property sites + public game finders.
=================================================================

    code/142_build_property_site_observations.py     built 2026-08-12

GAMING SPEC STEPS 11 AND 21.

WHAT THIS IS
------------
Two different things a casino publishes about itself, kept in two files because
they are two different KINDS of fact:

1. **Property-site observations** - what the operator says about its own SCALE:
   gaming floor square feet, slot/table/poker counts, hotel rooms, meeting and
   convention space, venue capacity, parking. Plus what its careers pages say
   about Indian Preference, wage floors and gaming-licence requirements.
   -> `data/clean/gaming_property_site_observations.csv`
   -> `data/clean/gaming_property_labor_demand.csv`

2. **Game-finder observations** - the public "find your game" systems that list
   game title, manufacturer, denomination and floor location.
   -> `data/clean/gaming_game_finder_observations.csv`

THE ONE RULE THAT ORGANISES FILE 2
----------------------------------
**A GAME LISTING IS NOT A CABINET.** Measured before a single row was counted,
on the Chickasaw Nation platform that powers WinStar / Riverwind / Newcastle:

    "$$$ Fever!"   Castle Hill Gaming   25c   -> map id geadfcc6...
    "$$$ Fever!"   Castle Hill Gaming   $1    -> map id g174f6b9...

Same title, same manufacturer, two rows, because the row is a
**(title x denomination x venue) SKU**, not a machine. A bank of forty
identical cabinets is one row; a title offered at three denominations is three.
WinStar's own page says so in as many words:

    "DISCLAIMER: Our Game Finder tool is as accurate as possible - but since
     we're constantly expanding, there may be differences or changes that
     aren't reflected here."

So every row is `measurement_type = GAME_FINDER_OBSERVATION`, `quantity` is
blank unless the source states one, and **the count of rows is never a device
count**. `ACTIVE_FLOOR_COUNT` is unreachable from this file by construction -
`GAME_FINDER_OBSERVATION` is in `cedar_domain.NEVER_PROMOTES_TO_ACTIVE`.

PROPERTY IDENTITY
-----------------
Attaches to existing `CCP-` / `VP-` / `TPL-` ids from `gaming_facilities.csv`.
**No new facility id is minted anywhere in this build** - asserted before write.
A site serving a different name for the same property is an alias, recorded in
`site_name_as_published`, never a second property.

PULL DISCIPLINE
---------------
`logs/_HOSTLOCK_<host>.json` claimed per host, >= 1.6s gap within a host,
sequential within a host, robots.txt honoured per path, single-shot fetches
with no retry loop, wall-clock deadline per phase, idempotent skip-if-present.
A transport failure (status 0) is recorded as a transport failure and is never
read as "the site does not publish this".

PHASES (run separately; each checkpoints)
-----------------------------------------
    --phase discover     candidate domains -> verified official sites
    --phase crawl        robots + sitemap + page selection + fetch
    --phase gamefinder   game-finder systems: detect, model, harvest
    --phase extract      parse everything on disk into the three CSVs
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html as htmllib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse as up
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
RAW = os.path.join(ROOT, "data", "raw", "external", "gaming_property_sites")
CLEAN = os.path.join(ROOT, "data", "clean")
INTERIM = os.path.join(ROOT, "data", "interim")
REVIEW = os.path.join(ROOT, "review")
LOGS = os.path.join(ROOT, "logs")
CODEBOOK = os.path.join(CLEAN, "codebook")
PAGES = os.path.join(RAW, "pages")
GF = os.path.join(RAW, "gamefinder")
for _d in (RAW, PAGES, GF, CLEAN, CODEBOOK, INTERIM, REVIEW, LOGS):
    os.makedirs(_d, exist_ok=True)

TODAY = dt.date.today().isoformat()
SCRIPT = "code/142_build_property_site_observations.py"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
GAP = 1.6

DOMAINS_CSV = os.path.join(INTERIM, "142_property_domains.csv")
CRAWL_CSV = os.path.join(INTERIM, "142_crawl_manifest.csv")
GF_CSV = os.path.join(INTERIM, "142_gamefinder_manifest.csv")

# Hosts owned by other builds, or that this build must never touch.
FORBIDDEN_HOSTS = {
    "files.usaspending.gov", "api.usaspending.gov", "apps.nd.gov",
    "www.treasurer.nd.gov", "www.nigc.gov", "nigc.gov", "web.archive.org",
    "api.sam.gov", "emma.msrb.org", "www.sec.gov", "efts.sec.gov",
}


# ---------------------------------------------------------------------------
# shared project code - one resolver, one domain vocabulary
# ---------------------------------------------------------------------------
def _load(mod_path, name):
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


sys.path.insert(0, CODE)
cedar_domain = _load(os.path.join(CODE, "cedar_domain.py"), "cedar_domain")
_p33 = _load(os.path.join(CODE, "33_apply_party_rulings.py"), "party_rulings_142")
resolve_entity = _p33.resolve_entity

MT = cedar_domain.MeasurementType
assert MT.GAME_FINDER_OBSERVATION in cedar_domain.NEVER_PROMOTES_TO_ACTIVE, (
    "GAME_FINDER_OBSERVATION must never be promotable to ACTIVE_FLOOR_COUNT")
assert not cedar_domain.may_promote(MT.GAME_FINDER_OBSERVATION,
                                    MT.ACTIVE_FLOOR_COUNT)


# ---------------------------------------------------------------------------
# host locks
# ---------------------------------------------------------------------------
def _lock_path(host):
    return os.path.join(LOGS, "_HOSTLOCK_%s.json" % host)


def claim_host(host, purpose):
    """True if we may poll this host. Appends to another live lock instead."""
    if host in FORBIDDEN_HOSTS:
        return False
    p = _lock_path(host)
    if os.path.exists(p):
        try:
            j = json.load(open(p, encoding="utf-8"))
        except Exception:
            j = {}
        if j.get("active"):
            claimed = j.get("claimed_at", "")
            try:
                age = (dt.datetime.now(dt.timezone.utc)
                       - dt.datetime.fromisoformat(claimed)).total_seconds()
            except Exception:
                age = 1e9
            if age < 6 * 3600 and j.get("pid") != os.getpid():
                j.setdefault("queue", []).append(
                    {"script": SCRIPT, "purpose": purpose, "queued_at": TODAY})
                json.dump(j, open(p, "w", encoding="utf-8"), indent=1)
                return False
    json.dump({"host": host, "pid": os.getpid(), "script": SCRIPT,
               "claimed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
               "active": True, "queue": [], "purpose": purpose,
               "policy": "single-shot fetches, >=1.6s gap, no retry loop, "
                         "robots.txt honoured"},
              open(p, "w", encoding="utf-8"), indent=1)
    return True


def release_host(host, note_text=""):
    p = _lock_path(host)
    if not os.path.exists(p):
        return
    try:
        j = json.load(open(p, encoding="utf-8"))
    except Exception:
        return
    j["active"] = False
    j["note"] = note_text
    j["released"] = dt.datetime.now(dt.timezone.utc).isoformat()
    json.dump(j, open(p, "w", encoding="utf-8"), indent=1)


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------
_last_hit = defaultdict(float)


def fetch(url, timeout=45, gap=GAP):
    """Single shot. Returns (status, body_bytes, effective_url). status 0 is a
    TRANSPORT FAILURE and is never read as a fact about the object."""
    host = up.urlsplit(url).netloc.lower()
    wait = gap - (time.time() - _last_hit[host])
    if wait > 0:
        time.sleep(wait)
    cmd = ["curl", "-s", "-L", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/xml;"
                 "q=0.9,application/json,application/pdf,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9",
           "--max-time", str(timeout), "--max-filesize", "12000000",
           "-w", "\n__S__%{http_code}__U__%{url_effective}", url]
    try:
        p = subprocess.run(cmd, capture_output=True)
    except Exception:
        _last_hit[host] = time.time()
        return 0, b"", url
    _last_hit[host] = time.time()
    out = p.stdout
    m = re.search(rb"\n__S__(\d+)__U__(\S*)$", out)
    if not m:
        return 0, out, url
    return int(m.group(1)), out[:m.start()], m.group(2).decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# robots.txt - honoured per path
# ---------------------------------------------------------------------------
_robots_cache = {}


def robots_rules(scheme_host):
    if scheme_host in _robots_cache:
        return _robots_cache[scheme_host]
    st, body, _ = fetch(scheme_host + "/robots.txt", timeout=25)
    dis, allow, sitemaps = [], [], []
    if st == 200:
        txt = decode(body)
        applies = False
        for line in txt.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            k, _, v = line.partition(":")
            k = k.strip().lower()
            v = v.strip()
            if k == "user-agent":
                applies = (v == "*")
            elif k == "sitemap":
                sitemaps.append(v)
            elif applies and k == "disallow" and v:
                dis.append(v)
            elif applies and k == "allow" and v:
                allow.append(v)
    r = {"status": st, "disallow": dis, "allow": allow, "sitemaps": sitemaps}
    _robots_cache[scheme_host] = r
    return r


def robots_ok(scheme_host, path):
    r = robots_rules(scheme_host)
    best_a = max((len(a) for a in r["allow"] if path.startswith(a.rstrip("*"))),
                 default=-1)
    best_d = max((len(d) for d in r["disallow"] if path.startswith(d.rstrip("*"))),
                 default=-1)
    return best_d <= best_a or best_d == -1


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------
def decode(body):
    """Some casino pages DECLARE utf-8 and serve windows-1252 (WinStar's game
    finder prints a cp1252 cent sign inside a page whose meta says UTF-8).
    Decoding strictly first and falling back keeps the denominations readable
    instead of turning every one of them into U+FFFD."""
    if isinstance(body, str):
        return body
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return body.decode("cp1252")
        except Exception:
            return body.decode("utf-8", "replace")


def to_text(body):
    t = decode(body)
    t = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>", "\n", t, flags=re.I)
    t = re.sub(r"</(p|div|li|tr|h\d|td|section)>", "\n", t, flags=re.I)
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", t))
    t = t.replace(" ", " ").replace("’", "'")
    lines = [re.sub(r"[ \t]+", " ", l).strip() for l in t.split("\n")]
    return "\n".join(l for l in lines if l)


GENERIC = {"casino", "casinos", "resort", "resorts", "hotel", "hotels", "and",
           "the", "of", "at", "a", "an", "inc", "llc", "gaming", "games",
           "center", "centre", "travel", "plaza", "stop", "smoke", "shop",
           "bingo", "hall", "club", "lodge", "spa", "grill", "express", "mart",
           "convenience", "store", "one", "two", "north", "south", "east",
           "west", "new", "old", "big", "little", "san", "united", "national"}


def norm_tokens(name):
    n = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower())
    return [t for t in n.split() if t]


def distinctive(name):
    return [t for t in norm_tokens(name) if t not in GENERIC and len(t) >= 3]


def slug(name):
    return "".join(norm_tokens(name))


def sha(b):
    return hashlib.md5(b).hexdigest()


def read_csv(p):
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p, rows, fields=None):
    if not rows:
        return 0
    fields = fields or list(rows[0].keys())
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def facilities():
    return read_csv(os.path.join(CLEAN, "gaming_facilities.csv"))


# ===========================================================================
# PHASE 1 - DISCOVER OFFICIAL PROPERTY DOMAINS
# ===========================================================================
# Seeds already proven by code/119_build_digital_and_loyalty.py.
SEED_HOSTS = [
    "www.fourwindscasino.com", "www.gunlakecasino.com",
    "www.firekeeperscasino.com", "www.soaringeaglecasino.com",
    "www.turtlecreekcasino.com", "www.odawacasino.com",
    "www.islandresortandcasino.com", "www.baymillscasino.com",
    "www.choctawcasinos.com", "www.cherokeecasino.com", "www.winstar.com",
    "www.ho-chunkgaming.com", "www.oneidacasino.net", "www.senecacasinos.com",
    "www.casinoarizona.com", "www.tulalipresortcasino.com",
    "www.muckleshootcasino.com", "www.pearlriverresort.com",
    "www.palacasino.com", "www.foxwoods.com", "mohegansun.com",
    "www.turningstone.com", "www.emeraldqueen.com", "www.windcreek.com",
    "www.wingilariver.com", "osagecasino.com", "shootingstarcasino.com",
    "www.ddcaz.com", "www.riverspirittulsa.com", "kewadin.com",
    "www.paysbig.com", "www.seminolehardrocktampa.com",
    "www.riverwind.com", "www.newcastlecasino.com", "www.coushattacasinoresort.com",
]

# Hand rulings, one per host, for sites the generated-candidate pass cannot
# reach or cannot split. Each names the property the SITE is about, with the
# reason. These are the only overrides in the build; nothing is snapped to a
# nearest match.
SEED_PROPERTY_RULINGS = {
    "www.winstar.com": ("CCP-411600",
        "winstar.com is the site of WinStar World Casino and Resort, "
        "Thackerville OK; its Game Finder's venue list is that property's own "
        "themed gaming plazas (Beijing, Cairo, London, Madrid, New York, "
        "Paris, Rio, Rome, Vienna) plus its Poker Room, Bingo Hall and high "
        "stakes salons. The name-generated candidate pass cannot reach it "
        "because the property name contains 'World' and the domain does not."),
    "www.riverwind.com": ("CCP-773500",
        "riverwind.com is the site of Riverwind Casino, Norman OK"),
    "www.newcastlecasino.com": ("CCP-410800",
        "newcastlecasino.com is the site of Newcastle Casino, Newcastle OK; "
        "Newcastle Gaming Center II and Newcastle Travel Plaza share the "
        "town name and are separate Cedar properties, and the Game Finder's "
        "venues are the casino's"),
    "www.coushattacasinoresort.com": ("CCP-38800",
        "coushattacasinoresort.com is the site of Coushatta Casino Resort, "
        "Kinder LA; the property carries no status literal in "
        "gaming_facilities.csv so it was outside the discovery frame"),
    "firekeeperscasino.com": ("CCP-658400",
        "firekeeperscasino.com is the site of FireKeepers Casino Hotel, "
        "Battle Creek MI"),
    "www.firekeeperscasino.com": ("CCP-658400",
        "firekeeperscasino.com is the site of FireKeepers Casino Hotel, "
        "Battle Creek MI"),
}

GAMING_WORDS = re.compile(
    r"\b(casino|slots?|slot machines|table games|gaming|players club|"
    r"rewards club|blackjack|bingo|sportsbook|jackpot)\b", re.I)


def candidates_for(fac):
    """Ordered candidate hosts generated from the property name."""
    name = fac["facility_name"]
    toks = norm_tokens(name)
    dis = distinctive(name)
    out = []

    def add(s):
        s = re.sub(r"[^a-z0-9]", "", s)
        if 4 <= len(s) <= 34:
            for tld in (".com", ".net"):
                out.append("www." + s + tld)

    if dis:
        add("".join(dis) + "casino")
        add("".join(dis))
    add("".join(toks))
    if dis:
        add("".join(dis) + "casinoresort")
        add("".join(dis[:2]) + "casino")
    seen, uniq = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq[:8]


def verify_host(fac, host):
    """Fetch a candidate root and decide whether it IS this property's site."""
    url = "https://" + host + "/"
    st, body, eff = fetch(url, timeout=20, gap=0.0)
    if st != 200 or len(body) < 2000:
        return None
    txt = to_text(body)
    low = txt.lower()
    if not GAMING_WORDS.search(low):
        return None
    dis = distinctive(fac["facility_name"])
    if not dis:
        return None
    hits = sum(1 for t in dis if t in low)
    city = (fac.get("city") or "").lower().strip()
    state = (fac.get("state") or "").strip()
    city_ok = bool(city) and city in low
    state_ok = bool(state) and re.search(r"\b%s\b" % re.escape(state), txt)
    # A site is accepted only when the page names the property AND places it.
    if hits < len(dis):
        return None
    if not (city_ok or state_ok):
        return None
    eff_host = up.urlsplit(eff).netloc.lower() or host
    return {"final_host": eff_host, "final_url": eff,
            "bytes": len(body),
            "city_on_page": "yes" if city_ok else "no",
            "state_on_page": "yes" if state_ok else "no",
            "distinctive_tokens": "|".join(dis)}


def phase_discover(limit, deadline):
    facs = [f for f in facilities()
            if f["property_status_literal"] in ("Open", "Temporarily Closed",
                                                "Under Construction")]
    facs.sort(key=lambda r: (r["state"], r["facility_name"]))
    done = {r["facility_id"] for r in read_csv(DOMAINS_CSV)}
    rows = read_csv(DOMAINS_CSV)
    todo = [f for f in facs if f["facility_id"] not in done][:limit]
    print("discover: %d open properties, %d already probed, %d to probe"
          % (len(facs), len(done), len(todo)))

    def work(fac):
        for host in candidates_for(fac):
            if time.time() > deadline:
                return None
            if host in FORBIDDEN_HOSTS:
                continue
            try:
                v = verify_host(fac, host)
            except Exception:
                v = None
            if v:
                return dict(facility_id=fac["facility_id"],
                            facility_name=fac["facility_name"],
                            tribe_id=fac.get("tribe_id", ""),
                            state=fac["state"], city=fac.get("city", ""),
                            candidate_host=host,
                            discovery_method="generated_from_property_name",
                            verified="yes", probed_date=TODAY, **v)
        return dict(facility_id=fac["facility_id"],
                    facility_name=fac["facility_name"],
                    tribe_id=fac.get("tribe_id", ""),
                    state=fac["state"], city=fac.get("city", ""),
                    candidate_host="", discovery_method="generated_from_property_name",
                    verified="no", probed_date=TODAY, final_host="", final_url="",
                    bytes="", city_on_page="", state_on_page="",
                    distinctive_tokens="|".join(distinctive(fac["facility_name"])))

    with ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(work, todo):
            if r:
                rows.append(r)
    write_csv(DOMAINS_CSV, rows)
    ok = sum(1 for r in rows if r["verified"] == "yes")
    print("discover: %d rows, %d verified" % (len(rows), ok))


# ===========================================================================
# PHASE 2 - CRAWL
# ===========================================================================
PATH_KEYWORDS = re.compile(
    r"/(casino|slots?|table-games|poker|sportsbook|about|history|press|news|"
    r"media|media-kit|press-room|hotel|rooms|suites|meeting|meetings|"
    r"convention|conventions|entertainment|venue|venues|restaurants|dining|"
    r"rewards|loyalty|players-club|career|careers|employment|jobs|map|maps|"
    r"game-finder|slot-finder|games|groups|sales|downloads|facts|fact-sheet|"
    r"our-story|resort|amenities|weddings|events-and-meetings|banquet)",
    re.I)

BLIND_PATHS = ["/casino/", "/slots/", "/table-games/", "/poker/", "/about/",
               "/hotel/", "/meetings/", "/careers/", "/press/", "/news/",
               "/entertainment/", "/game-finder/", "/slot-finder/",
               "/casino-map/", "/media-kit/", "/groups/"]

MAX_PAGES_PER_HOST = 16


def sitemap_urls(scheme_host, robots, budget=4):
    """Enumerate sitemaps (index-aware, one level deep). Returns url list."""
    urls, seen = [], set()
    queue = list(robots["sitemaps"]) or [scheme_host + "/sitemap.xml",
                                         scheme_host + "/sitemap_index.xml"]
    fetched = 0
    while queue and fetched < budget:
        sm = queue.pop(0)
        if sm in seen:
            continue
        seen.add(sm)
        st, body, _ = fetch(sm, timeout=40)
        fetched += 1
        if st != 200:
            continue
        txt = decode(body)
        locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", txt, re.S)
        if "<sitemapindex" in txt.lower():
            for l in locs:
                if re.search(r"(page|post|casino|game|career|about|venue)", l, re.I):
                    queue.append(htmllib.unescape(l))
        else:
            urls.extend(htmllib.unescape(l) for l in locs)
    return urls


def select_pages(scheme_host, urls):
    """Rank sitemap URLs; keep the SCALE-bearing ones first."""
    prio = [
        (re.compile(r"/(meeting|convention|group|sales|banquet|events-and-meetings|"
                    r"weddings|venue)", re.I), 0),
        (re.compile(r"/(about|our-story|history|fact|press|media|news)", re.I), 1),
        (re.compile(r"/(career|employment|jobs)", re.I), 2),
        (re.compile(r"/(casino|slot|table-game|poker|gaming|game)", re.I), 3),
        (re.compile(r"/(hotel|room|suite|amenit|resort)", re.I), 4),
    ]
    scored = []
    for u in urls:
        if not u.startswith(scheme_host):
            continue
        path = up.urlsplit(u).path
        if not PATH_KEYWORDS.search(path):
            continue
        if path.count("/") > 5:
            continue
        rank = 9
        for rx, r in prio:
            if rx.search(path):
                rank = min(rank, r)
        scored.append((rank, len(path), u))
    scored.sort()
    out, seen = [], set()
    for _, _, u in scored:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out[:MAX_PAGES_PER_HOST]


def page_file(host, url):
    return os.path.join(PAGES, "%s__%s.html" % (re.sub(r"[^a-z0-9.]", "_", host),
                                                sha(url.encode())[:16]))


def phase_crawl(limit, deadline):
    doms = [r for r in read_csv(DOMAINS_CSV) if r["verified"] == "yes"]
    by_host = defaultdict(list)
    for r in doms:
        by_host[r["final_host"]].append(r)
    for h in SEED_HOSTS:
        by_host.setdefault(h, [])
    man = read_csv(CRAWL_CSV)
    done_hosts = {r["host"] for r in man}
    hosts = [h for h in sorted(by_host) if h and h not in done_hosts][:limit]
    print("crawl: %d hosts known, %d already crawled, %d this run"
          % (len(by_host), len(done_hosts), len(hosts)))

    import threading
    lk = threading.Lock()

    def do_host(host):
        if time.time() > deadline:
            return
        if not claim_host(host, "official property site sweep (spec step 21)"):
            with lk:
                man.append(dict(host=host, url="", http_status="", bytes="",
                                file="", robots="host lock held by another agent",
                                fetched_date=TODAY, note="SKIPPED - lock held"))
            return
        sh = "https://" + host
        rows = []
        try:
            rb = robots_rules(sh)
            if rb["status"] == 0:
                rows.append(dict(host=host, url=sh + "/robots.txt", http_status="0",
                                 bytes="", file="", robots="transport failure",
                                 fetched_date=TODAY,
                                 note="TRANSPORT FAILURE - not a fact about the site"))
                release_host(host, "transport failure on robots.txt")
                with lk:
                    man.extend(rows)
                return
            urls = sitemap_urls(sh, rb)
            sel = select_pages(sh, urls)
            method = "sitemap"
            if not sel:
                sel = [sh + p2 for p2 in BLIND_PATHS]
                method = "blind_path_probe"
            sel = [sh + "/"] + [u for u in sel if u != sh + "/"]
            n_ok = 0
            for u in sel[:MAX_PAGES_PER_HOST + 1]:
                if time.time() > deadline:
                    break
                path = up.urlsplit(u).path or "/"
                if not robots_ok(sh, path):
                    rows.append(dict(host=host, url=u, http_status="", bytes="",
                                     file="", robots="DISALLOWED",
                                     fetched_date=TODAY,
                                     note="refused by robots.txt - not fetched"))
                    continue
                fp = page_file(host, u)
                if os.path.exists(fp):
                    continue
                st, body_b, eff = fetch(u, timeout=40)
                if st == 200 and body_b:
                    with open(fp, "wb") as f:
                        f.write(body_b)
                    n_ok += 1
                rows.append(dict(host=host, url=u, http_status=str(st),
                                 bytes=str(len(body_b)),
                                 file=os.path.basename(fp) if st == 200 else "",
                                 robots="allowed", fetched_date=TODAY,
                                 note="page selection = " + method
                                      + ("" if st else
                                         " | TRANSPORT FAILURE, not a 404")))
                if st in (403, 429):
                    rows.append(dict(host=host, url=u, http_status=str(st),
                                     bytes="", file="", robots="allowed",
                                     fetched_date=TODAY,
                                     note="REFUSAL - stopped this host"))
                    break
            release_host(host, "%d pages retrieved" % n_ok)
        except Exception as e:
            release_host(host, "error: %s" % e)
            rows.append(dict(host=host, url="", http_status="", bytes="",
                             file="", robots="", fetched_date=TODAY,
                             note="ERROR %s" % e))
        with lk:
            man.extend(rows)
            write_csv(CRAWL_CSV, man)

    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(do_host, hosts))
    write_csv(CRAWL_CSV, man)
    print("crawl: manifest %d rows" % len(man))


# ===========================================================================
# PHASE 3 - GAME FINDERS
# ===========================================================================
# Platform 1: the Chickasaw Nation WordPress theme. Custom post type
# `wscp_casino_game`, taxonomy `wscp_casino_game_category`, venue taxonomy
# `wscp_casino_game_venue`. Archive at /gaming/casino-games/list/, 20 per page,
# `?page=N`, `data-max-pages` printed in the Load More control.
CHICKASAW_LIST = "/gaming/casino-games/list/"

# Platform 2: the Coushatta "Slot Finder". A bespoke PHP application whose
# result fragment is served unauthenticated at /ajax-slot-result.php with GET
# criteria (title, denom, manu, type, volatil). It refuses an empty query -
# "Please enter a slot name, denomination, or a manufacturer" - so the harvest
# iterates its OWN published manufacturer list, one request each.
COUSHATTA_FORM = "/gaming/slot-search/"
COUSHATTA_AJAX = "/ajax-slot-result.php"

# Any page carrying one of these is a game-finder SIGNAL. Recorded even where
# no harvest route exists, because "a finder is published here" is itself the
# coverage fact.
GF_SIGNALS = re.compile(
    r"(slot ?finder|find ?a ?slot|game ?finder|find your game|all slots|"
    r"games list|casino games list|interactive map|casino map|"
    r"progressive jackpots?)", re.I)


def parse_coushatta(txt):
    """One <tr> = one (title x denomination) listing with its own map sid."""
    out = []
    for tr in re.split(r"<tr>", txt)[1:]:
        cap = re.search(r'<span class="caption">(.*?)</span>', tr, re.S)
        if not cap:
            continue
        c = cap.group(1)

        def fld(label):
            m = re.search(label + r":\s*<strong>(.*?)</strong>", c, re.S)
            return htmllib.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() \
                if m else ""

        title = fld("Title")
        if not title:
            continue
        sid = re.search(r"slot-map\.php\?sid=(\d+)", tr)
        out.append({"game_title": title, "manufacturer": fld("Manufacturer"),
                    "denomination": fld("Denomination"),
                    "game_type": fld("Type"), "volatility": fld("Volatility"),
                    "source_game_id": ("sid=" + sid.group(1)) if sid else ""})
    return out


def gf_file(host, tag):
    return os.path.join(GF, "%s__%s.html" % (re.sub(r"[^a-z0-9.]", "_", host), tag))


def parse_chickasaw(txt):
    """One <div class="casino-game-wrap"> = one (title x denomination) listing."""
    out = []
    for blk in re.split(r'<div id="[^"]*" class="casino-game-wrap">', txt)[1:]:
        blk = blk.split("<!-- .casino-game-wrap -->")[0]
        t = re.search(r'casino-game-title[^>]*>\s*(.*?)\s*</h2>', blk, re.S)
        if not t:
            continue
        title = htmllib.unescape(re.sub(r"<[^>]+>", "", t.group(1))).strip()
        man = re.search(r'casino-game-label manufacturer">\s*(.*?)\s*</h6>', blk, re.S)
        manu = ""
        if man:
            manu = htmllib.unescape(re.sub(r"<[^>]+>", "", man.group(1)))
            manu = manu.replace(" ", " ").strip(" •*-·").strip()
        den = re.findall(r"game-amount'>(.*?)</span>", blk)
        den = " | ".join(htmllib.unescape(d).replace(" ", " ").strip()
                         for d in den)
        gid = re.search(r"game-id=(g[0-9a-f]{6,})", blk)
        if title:
            out.append({"game_title": title, "manufacturer": manu,
                        "denomination": den,
                        "source_game_id": gid.group(1) if gid else ""})
    return out


def phase_gamefinder(limit, deadline, only=None):
    doms = [r for r in read_csv(DOMAINS_CSV) if r["verified"] == "yes"]
    hosts = {}
    for r in doms:
        hosts.setdefault(r["final_host"], r)
    for h in SEED_HOSTS:
        hosts.setdefault(h, None)
    if only:
        hosts = {h: v for h, v in hosts.items() if h in only}
    man = read_csv(GF_CSV)
    done = {(r["host"], r["tag"]) for r in man}
    n = 0
    for host in sorted(hosts):
        if n >= limit or time.time() > deadline:
            break
        if (host, "detect") in done:
            continue
        _dp = gf_file(host, "detect")
        if not claim_host(host, "public game-finder detection (spec step 11)"):
            continue
        sh = "https://" + host
        try:
            if not robots_ok(sh, CHICKASAW_LIST):
                man.append(dict(host=host, tag="detect", url=sh + CHICKASAW_LIST,
                                http_status="", platform="", file="",
                                fetched_date=TODAY, note="robots DISALLOWED"))
                release_host(host, "robots disallowed")
                continue
            st, body, eff = fetch(sh + CHICKASAW_LIST, timeout=45)
            txt = decode(body)
            platform = ""
            if st == 200 and "casino-game-wrap" in txt:
                platform = "chickasaw_wscp_casino_game"
            fp = gf_file(host, "detect")
            if st == 200:
                open(fp, "wb").write(body)
            man.append(dict(host=host, tag="detect", url=sh + CHICKASAW_LIST,
                            http_status=str(st), platform=platform,
                            file=os.path.basename(fp) if st == 200 else "",
                            fetched_date=TODAY,
                            note="" if st else "TRANSPORT FAILURE, not a 404"))
            n += 1
            if platform == "chickasaw_wscp_casino_game":
                # THE VENUE FILTER DOES NOT FILTER. Measured 2026-08-12:
                # www.winstar.com/gaming/casino-games/list/?...&
                # wscp_casino_game_venue=41187 (Baccarat Salon) returns the
                # SAME first page as the unfiltered archive, and Newcastle
                # venues 1 and 3 return identical pages. Riverwind publishes no
                # venue dropdown at all. So the venue select is a UI control
                # this request shape does not honour, and writing its label
                # into floor_location would have attributed every game at
                # WinStar to a Baccarat Salon. The venue LIST is kept as a
                # published fact about the property's named gaming areas; it is
                # never joined to a game.
                venues = dict(re.findall(
                    r'<option\s+value="(\d+)">([^<]+)</option>', txt))
                if venues:
                    man.append(dict(host=host, tag="venues", url=sh + CHICKASAW_LIST,
                                    http_status="200", platform=platform, file="",
                                    fetched_date=TODAY,
                                    note="named gaming areas published by the "
                                         "finder (NOT joined to any game, the "
                                         "filter is inert): "
                                         + "; ".join(sorted(venues.values()))))
                cats = re.findall(
                    r"<option class=\"level-0\" value='?\"?([a-z0-9\-]+)'?\"?", txt)
                cats = [c for c in dict.fromkeys(cats)] or ["electronic-games"]
                for cat in cats:
                    page, maxp = 1, 1
                    while page <= maxp and page <= 200:
                        if time.time() > deadline:
                            break
                        q = {"post_type": "wscp_casino_game",
                             "wscp_casino_game_category": cat, "page": str(page)}
                        u = sh + CHICKASAW_LIST + "?" + up.urlencode(q)
                        tag = "cat-%s_p%d" % (cat, page)
                        fp2 = gf_file(host, tag)
                        if os.path.exists(fp2):
                            t2 = decode(open(fp2, "rb").read())
                        else:
                            st2, b2, _ = fetch(u, timeout=45)
                            if st2 != 200:
                                man.append(dict(host=host, tag=tag, url=u,
                                                http_status=str(st2),
                                                platform=platform, file="",
                                                fetched_date=TODAY,
                                                note="stop" if st2 else
                                                "TRANSPORT FAILURE, not a 404"))
                                break
                            open(fp2, "wb").write(b2)
                            t2 = decode(b2)
                        mp = re.search(r'data-max-pages="(\d+)"', t2)
                        if mp:
                            maxp = int(mp.group(1))
                        man.append(dict(host=host, tag=tag, url=u,
                                        http_status="200", platform=platform,
                                        file=os.path.basename(fp2),
                                        fetched_date=TODAY,
                                        note="category=%s max_pages=%d "
                                             "(no venue filter - it is inert)"
                                             % (cat, maxp)))
                        if not parse_chickasaw(t2):
                            break
                        page += 1
            # ---- platform 2: Coushatta-style slot search ----
            if not platform and robots_ok(sh, COUSHATTA_FORM):
                st3, b3, _ = fetch(sh + COUSHATTA_FORM, timeout=45)
                t3 = decode(b3)
                if st3 == 200 and 'name="slotsForm"' in t3:
                    platform = "coushatta_slot_search"
                    fp = gf_file(host, "detect2")
                    open(fp, "wb").write(b3)
                    manus = re.findall(
                        r'<select id="manu"[^>]*>(.*?)</select>', t3, re.S)
                    opts = re.findall(r'<option value="([^"]+)">', manus[0]) \
                        if manus else []
                    man.append(dict(host=host, tag="detect2",
                                    url=sh + COUSHATTA_FORM, http_status="200",
                                    platform=platform,
                                    file=os.path.basename(fp), fetched_date=TODAY,
                                    note="manufacturers published by the finder: "
                                         + "; ".join(opts)))
                    if robots_ok(sh, COUSHATTA_AJAX):
                        for mf in opts:
                            if time.time() > deadline:
                                break
                            tag = "manu-" + re.sub(r"\W+", "_", mf)
                            fp2 = gf_file(host, tag)
                            u = (sh + COUSHATTA_AJAX + "?"
                                 + up.urlencode({"title": "", "denom": "",
                                                 "manu": mf, "type": "",
                                                 "volatil": ""}))
                            if os.path.exists(fp2):
                                man.append(dict(host=host, tag=tag, url=u,
                                                http_status="200",
                                                platform=platform,
                                                file=os.path.basename(fp2),
                                                fetched_date=TODAY,
                                                note="manufacturer=%s (from cache)"
                                                     % mf))
                                continue
                            st4, b4, _ = fetch(u, timeout=45)
                            if st4 != 200:
                                man.append(dict(host=host, tag=tag, url=u,
                                                http_status=str(st4),
                                                platform=platform, file="",
                                                fetched_date=TODAY,
                                                note="stop" if st4 else
                                                "TRANSPORT FAILURE"))
                                break
                            open(fp2, "wb").write(b4)
                            man.append(dict(host=host, tag=tag, url=u,
                                            http_status="200", platform=platform,
                                            file=os.path.basename(fp2),
                                            fetched_date=TODAY,
                                            note="manufacturer=%s" % mf))
                    else:
                        man.append(dict(host=host, tag="ajax", url=sh + COUSHATTA_AJAX,
                                        http_status="", platform=platform, file="",
                                        fetched_date=TODAY,
                                        note="robots DISALLOWED - finder found, "
                                             "not harvested"))
            release_host(host, "game-finder detect platform=%s" % (platform or "none"))
        except Exception as e:
            release_host(host, "error %s" % e)
            man.append(dict(host=host, tag="detect", url="", http_status="",
                            platform="", file="", fetched_date=TODAY,
                            note="ERROR %s" % e))
        write_csv(GF_CSV, man)
    write_csv(GF_CSV, man)
    print("gamefinder: manifest %d rows" % len(man))


# ===========================================================================
# PHASE 4 - EXTRACT
# ===========================================================================
NUM = r"([0-9][0-9,\.]{0,12})"

METRIC_PATTERNS = [
    ("gaming_machines", "count",
     re.compile(r"\b(?:more than|over|nearly|approximately|about|almost)?\s*"
                + NUM + r"\+?\s*(?:of the (?:latest|newest) )?"
                r"(?:electronic |video |reel |class ii |class iii )*"
                r"(?:slot machines|slots|electronic games|gaming machines|"
                r"electronic gaming machines|games)\b", re.I)),
    ("table_games", "count",
     re.compile(r"\b(?:more than|over|nearly|approximately|about)?\s*" + NUM
                + r"\+?\s*(?:live |exciting )*table games\b", re.I)),
    ("poker_tables", "count",
     re.compile(r"\b(?:more than|over|nearly|approximately|about)?\s*" + NUM
                + r"\+?\s*poker tables\b", re.I)),
    ("bingo_seats", "seats",
     re.compile(r"\b" + NUM + r"\+?\s*(?:bingo )?seats?\b(?=[^.]{0,40}bingo)", re.I)),
    ("hotel_rooms", "rooms",
     re.compile(r"\b(?:more than|over|nearly|approximately|about)?\s*" + NUM
                + r"\+?\s*(?:luxurious |well-appointed |spacious |guest |"
                  r"hotel )*(?:rooms and suites|guest rooms|guestrooms|"
                  r"hotel rooms|rooms)\b", re.I)),
    ("gaming_square_feet", "sqft",
     re.compile(NUM + r"\s*(?:\+|plus)?\s*(?:-|–)?\s*square[- ]f(?:ee|oo)t"
                r"(?:\s+of)?\s+(?:gaming|casino)\b", re.I)),
    ("gaming_square_feet", "sqft",
     re.compile(r"\b(?:gaming|casino)\s+(?:floor\s+)?(?:space|area|floor)"
                r"[^.\n]{0,30}?" + NUM + r"\s*(?:square feet|sq\.? ?ft)", re.I)),
    ("meeting_square_feet", "sqft",
     re.compile(NUM + r"\s*(?:\+|plus)?\s*(?:square feet|sq\.? ?ft\.?)"
                r"[^.\n]{0,40}?(?:meeting|convention|event|banquet|"
                r"flexible|function)\b", re.I)),
    ("meeting_square_feet", "sqft",
     re.compile(r"\b(?:meeting|convention|event|banquet|exhibit)[^.\n]{0,40}?"
                + NUM + r"\s*(?:square feet|sq\.? ?ft)", re.I)),
    ("venue_capacity", "persons",
     re.compile(r"\b(?:seats?|accommodat\w+|holds?|capacity of|up to)\s+(?:up to\s+)?"
                + NUM + r"\s*(?:guests|people|persons|patrons|fans|seats)\b", re.I)),
    ("parking_spaces", "spaces",
     re.compile(NUM + r"\+?\s*(?:covered |free )*parking (?:spaces|spots)\b", re.I)),
    ("restaurants", "count",
     re.compile(NUM + r"\+?\s*(?:award-winning |signature |unique )*"
                r"(?:restaurants|dining options|dining outlets|eateries)\b", re.I)),
]

# careers / labour-demand language
PREF_PATTERNS = [
    ("indian_preference", re.compile(
        r"[^\n]{0,160}\b(indian preference|native american preference|"
        r"tribal member preference|tribal preference|member preference|"
        r"preference (?:in hiring|will be given)[^\n]{0,80}(?:indian|tribal|native))"
        r"[^\n]{0,200}", re.I)),
    ("gaming_license_required", re.compile(
        r"[^\n]{0,160}\b(gaming licen[cs]e|licen[cs]ed by the (?:tribal )?gaming "
        r"commission|must be able to obtain[^\n]{0,60}gaming licen[cs]e)"
        r"[^\n]{0,200}", re.I)),
    ("wage_floor", re.compile(
        r"[^\n]{0,140}\$\s?([0-9]{1,2}(?:\.[0-9]{2})?)\s*(?:/|per )\s?(?:hour|hr)"
        r"[^\n]{0,140}", re.I)),
    ("tribal_employment_rights", re.compile(
        r"[^\n]{0,160}\b(TERO|tribal employment rights)[^\n]{0,200}", re.I)),
]

# ---- the guard that keeps a GAME TITLE from becoming a slot count ----
# Measured on the first extraction pass: "Sugar Rush 1000 Slots" and
# "Fire 88 Slots" are jackpot-ticker GAME TITLES, and a bare
# number-next-to-noun rule read them as 1,000 and 88 machines. A date in the
# same ticker ("8/9/2026 ... Slots") became 2,026 machines. So a number is
# accepted ONLY when a counting cue immediately precedes it, and refused
# candidates are written to review/ rather than dropped silently.
CUE_WORDS = {
    "over", "than", "nearly", "approximately", "about", "almost", "with",
    "featuring", "features", "feature", "featured", "offers", "offer",
    "offering", "boasts", "boast", "boasting", "houses", "house", "housing",
    "and", "to", "our", "has", "have", "having", "includes", "include",
    "including", "play", "enjoy", "experience", "discover", "choose", "from",
    "of", "spanning", "total", "are", "is", "the", "than", "between", "up",
    "we", "casino", "floor", "than", "now", "boastsover", "some", "all",
}
QUALIFIER_HEAD = re.compile(
    r"^\s*(more than|over|nearly|approximately|about|almost|up to)\b", re.I)
DATE_NEAR = re.compile(r"(\d{1,2}/\d{1,2}/\d{2,4}|\b20\d\d\b)")


def has_counting_cue(text, m):
    """True if a counting cue precedes the number, or the match carries one."""
    if QUALIFIER_HEAD.search(m.group(0)):
        return True
    before = text[max(0, m.start() - 60):m.start()]
    if DATE_NEAR.search(before[-14:]):
        return False
    w = re.findall(r"[A-Za-z']+", before)
    if not w:
        return False
    return w[-1].lower() in CUE_WORDS


BAD_CONTEXT = re.compile(
    r"(square feet of retail|per person|per night|\$|percent|%|"
    r"years|calories|reward points|points)", re.I)


def plausible(metric, val):
    if val is None:
        return False
    if metric in ("gaming_machines",):
        return 20 <= val <= 15000
    if metric in ("table_games", "poker_tables", "restaurants"):
        return 1 <= val <= 400
    if metric == "hotel_rooms":
        return 5 <= val <= 4000
    if metric == "bingo_seats":
        return 20 <= val <= 5000
    if metric in ("gaming_square_feet", "meeting_square_feet"):
        return 1000 <= val <= 1200000
    if metric == "venue_capacity":
        return 50 <= val <= 100000
    if metric == "parking_spaces":
        return 20 <= val <= 30000
    return False


def tonum(s):
    try:
        s = s.replace(",", "").rstrip(".")
        return float(s)
    except Exception:
        return None


def snippet(text, start, end, pad=110):
    a = max(0, start - pad)
    b = min(len(text), end + pad)
    return re.sub(r"\s+", " ", text[a:b]).strip()



def merge_dated(path, new_rows, key_fields, value_fields, id_prefix):
    """Append-only history. An observation is NEVER overwritten.

    A row whose identity AND value are unchanged only has its `last_seen`
    refreshed - that is what keeps a daily re-run from writing thousands of
    identical snapshots. A row whose value has MEANINGFULLY CHANGED is appended
    as a new dated observation beside the old one, which stays exactly as it
    was."""
    old = read_csv(path)
    idx = {}
    for r in old:
        idx[tuple(r.get(k, "") for k in key_fields)] = r
    kept, appended, refreshed = list(old), 0, 0
    seq = len(old)
    for r in new_rows:
        k = tuple(r.get(f, "") for f in key_fields)
        prev = idx.get(k)
        if prev is not None and all(prev.get(v, "") == r.get(v, "")
                                    for v in value_fields):
            prev["last_seen"] = r["last_seen"]
            refreshed += 1
            continue
        seq += 1
        r["observation_id"] = "%s-%06d" % (id_prefix, seq)
        r["supersedes_observation_id"] = prev["observation_id"] if prev else ""
        kept.append(r)
        idx[k] = r
        appended += 1
    fields = list(kept[0].keys()) if kept else []
    for r in kept:
        for f in fields:
            r.setdefault(f, "")
    write_csv(path, kept, fields)
    print("  %s: %d existing, %d refreshed, %d appended -> %d"
          % (os.path.basename(path), len(old), refreshed, appended, len(kept)))
    return len(kept)


def attribute(host, props):
    """Which Cedar property is this host about? Ruling first, then a single
    verified link, then refusal - never a nearest match."""
    if host in SEED_PROPERTY_RULINGS:
        fid, why = SEED_PROPERTY_RULINGS[host]
        return fid, "hand_ruling: " + why
    if len(props) == 1:
        return props[0]["facility_id"], "single_property_host"
    if len(props) > 1:
        return "", ("multi_property_host: %d Cedar properties resolve to this "
                    "host (%s) - not attributable to one property"
                    % (len(props), ", ".join(p["facility_id"] for p in props)))
    return "", ("seed_host_with_no_verified_property_link - recorded, not "
                "snapped to a nearest property")


def phase_extract():
    facs = facilities()
    valid_ids = {f["facility_id"] for f in facs}
    fac_by_id = {f["facility_id"]: f for f in facs}
    doms = [r for r in read_csv(DOMAINS_CSV) if r["verified"] == "yes"]
    host_props = defaultdict(list)
    for r in doms:
        host_props[r["final_host"]].append(r)

    # A host that serves several Cedar properties (windcreek.com, kewadin.com)
    # cannot have a page attributed to one of them. Those hosts are recorded
    # MULTI and their observations are written with a blank facility_id and a
    # named reason rather than snapped to a nearest property.
    man = read_csv(CRAWL_CSV)
    by_file = {r["file"]: r for r in man if r.get("file")}

    obs, labor, refused = [], [], []
    seen_obs = set()
    seq = 0
    lab_seq = 0
    for fname, mrow in sorted(by_file.items()):
        fp = os.path.join(PAGES, fname)
        if not os.path.exists(fp):
            continue
        host = mrow["host"]
        props = host_props.get(host, [])
        url = mrow["url"]
        raw = open(fp, "rb").read()
        text = to_text(raw)
        if len(text) < 300:
            continue
        path = up.urlsplit(url).path.lower()
        is_careers = bool(re.search(r"(career|employment|jobs|hiring)", path))

        fid, attrib = attribute(host, props)

        # ---- SCALE metrics ----
        for metric, unit, rx in METRIC_PATTERNS:
            for m in rx.finditer(text):
                val = tonum(m.group(1))
                if not plausible(metric, val):
                    continue
                quote = snippet(text, m.start(), m.end())
                if not has_counting_cue(text, m):
                    refused.append(dict(site_host=host, source_url=url,
                                        metric=metric, value=m.group(1),
                                        refusal_reason=("no counting cue before "
                                                        "the number - reads as a "
                                                        "game title or a date"),
                                        source_quote=quote,
                                        retrieved_at=mrow["fetched_date"]))
                    continue
                key = (host, metric, "%g" % val, re.sub(r"\W+", "", quote)[:80])
                if key in seen_obs:
                    continue
                seen_obs.add(key)
                seq += 1
                obs.append(dict(
                    observation_id="GPS-%05d" % seq,
                    facility_id=fid if fid in valid_ids else "",
                    facility_name=(fac_by_id.get(fid, {}).get("facility_name", "")
                                   if fid else ""),
                    tribe_id=(fac_by_id.get(fid, {}).get("tribe_id", "") if fid else ""),
                    state=(fac_by_id.get(fid, {}).get("state", "") if fid else ""),
                    site_host=host,
                    site_name_as_published="",
                    metric=metric, value="%g" % val, unit=unit,
                    measurement_type=MT.PROPERTY_REPORTED_COUNT.value,
                    measurement_basis=("the operator's own public website; the "
                                       "operator does not state a count date"),
                    page_class=("careers" if is_careers else "property_page"),
                    source_url=url,
                    source_quote=quote,
                    retrieved_at=mrow["fetched_date"],
                    as_of_date=mrow["fetched_date"],
                    as_of_date_precision="observed_on_retrieval_date",
                    first_seen=mrow["fetched_date"],
                    last_seen=mrow["fetched_date"],
                    supersedes_observation_id="",
                    attribution_basis=attrib,
                    confidence="B" if fid else "C",
                    source_md5=sha(raw),
                    built_by_script=SCRIPT, built_date=TODAY))

        # ---- labour demand / preference language ----
        if is_careers or re.search(r"(indian preference|tribal member preference)",
                                   text, re.I):
            for kind, rx in PREF_PATTERNS:
                for m in list(rx.finditer(text))[:6]:
                    lab_seq += 1
                    labor.append(dict(
                        observation_id="GPL-%05d" % lab_seq,
                        facility_id=fid if fid in valid_ids else "",
                        facility_name=(fac_by_id.get(fid, {}).get("facility_name", "")
                                       if fid else ""),
                        tribe_id=(fac_by_id.get(fid, {}).get("tribe_id", "")
                                  if fid else ""),
                        site_host=host,
                        provision_type=kind,
                        value=(m.group(1) if kind == "wage_floor" else ""),
                        unit=("usd_per_hour" if kind == "wage_floor" else ""),
                        observation_class="LABOR_DEMAND_STATEMENT",
                        measurement_type="LABOR_DEMAND_STATEMENT",
                        measurement_type_note=(
                            "deliberately OUTSIDE cedar_domain.MeasurementType: "
                            "a job posting or a preference policy measures "
                            "nothing about capacity and must never join the "
                            "count vocabulary"),
                        not_an_employee_count=("an open posting or a policy "
                                               "statement is labour DEMAND; it is "
                                               "never an employee count"),
                        source_url=url,
                        source_quote=re.sub(r"\s+", " ", m.group(0)).strip()[:600],
                        retrieved_at=mrow["fetched_date"],
                        first_seen=mrow["fetched_date"],
                        last_seen=mrow["fetched_date"],
                        supersedes_observation_id="",
                        attribution_basis=attrib,
                        confidence="B" if fid else "C",
                        source_md5=sha(raw),
                        built_by_script=SCRIPT, built_date=TODAY))

    # ---- game finder ----
    gman = read_csv(GF_CSV)
    gf_rows = []
    g_seq = 0
    for r in gman:
        plat = r.get("platform") or ""
        if plat not in ("chickasaw_wscp_casino_game", "coushatta_slot_search"):
            continue
        if not r.get("file") or r["tag"].startswith("detect"):
            continue
        fp = os.path.join(GF, r["file"])
        if not os.path.exists(fp):
            continue
        raw = open(fp, "rb").read()
        txt = decode(raw)
        host = r["host"]
        props = host_props.get(host, [])
        fid, attrib = attribute(host, props)
        if plat == "chickasaw_wscp_casino_game":
            venue = ""
            cm = re.search(r"category=([a-z0-9\-]+)", r.get("note", ""))
            cat = cm.group(1) if cm else ""
            parsed = parse_chickasaw(txt)
            unit = "title_denomination_listing"
            floor_basis = ("BLANK BY MEASUREMENT: the finder prints a venue "
                           "dropdown but the server ignores it - WinStar's "
                           "Baccarat Salon filter returns the unfiltered first "
                           "page and Newcastle venues 1 and 3 are identical, so "
                           "no game can be placed in a named area. The venue "
                           "list itself is recorded in the crawl manifest.")
        else:
            venue, cat = "", ""
            parsed = parse_coushatta(txt)
            unit = "title_denomination_listing"
            floor_basis = ("the finder plots a pixel marker on a floor-plan SVG "
                           "(slot-map.php?sid=N) and publishes no named zone; "
                           "the map id is kept in source_game_id")
        for g in parsed:
            g_seq += 1
            gf_rows.append(dict(
                observation_id="GFO-%06d" % g_seq,
                facility_id=fid if fid in valid_ids else "",
                facility_name=(fac_by_id.get(fid, {}).get("facility_name", "")
                               if fid else ""),
                tribe_id=(fac_by_id.get(fid, {}).get("tribe_id", "") if fid else ""),
                state=(fac_by_id.get(fid, {}).get("state", "") if fid else ""),
                site_host=host,
                game_title=g["game_title"],
                manufacturer=g["manufacturer"],
                denomination=g["denomination"],
                floor_location=venue,
                floor_location_basis=floor_basis,
                game_category=cat or g.get("game_type", ""),
                volatility_as_published=g.get("volatility", ""),
                quantity_if_known="",
                quantity_absent_reason=(
                    "the finder publishes no quantity; a listing is a "
                    "(title x denomination) SKU, not a cabinet"),
                measurement_type="GAME_FINDER_OBSERVATION",
                listing_unit=unit,
                is_device_count="no",
                source_game_id=g["source_game_id"],
                first_seen=r["fetched_date"], last_seen=r["fetched_date"],
                supersedes_observation_id="",
                source="operator public game finder (%s platform)" % plat,
                source_url=r["url"],
                source_quote="%s | %s | %s | %s" % (
                    g["game_title"], g["manufacturer"] or "(no manufacturer stated)",
                    g["denomination"] or "(no denomination stated)",
                    venue or g.get("game_type", "") or "(no venue published)"),
                retrieved_at=r["fetched_date"],
                attribution_basis=attrib,
                confidence="B" if fid else "C",
                source_md5=sha(raw),
                built_by_script=SCRIPT, built_date=TODAY))

    # ---- game-finder SIGNALS: a finder published but not harvested ----
    signals = []
    for fname, mrow in sorted(by_file.items()):
        fpx = os.path.join(PAGES, fname)
        if not os.path.exists(fpx):
            continue
        t = to_text(open(fpx, "rb").read())
        for m in GF_SIGNALS.finditer(t):
            signals.append(dict(site_host=mrow["host"], source_url=mrow["url"],
                                signal=m.group(0),
                                source_quote=snippet(t, m.start(), m.end()),
                                retrieved_at=mrow["fetched_date"]))
            break
    write_csv(os.path.join(REVIEW, "gaming_game_finder_signals_%s.csv" % TODAY),
              signals)

    # ---- the systems themselves, and what each one's ROW MEANS ----
    harvested = Counter(r["site_host"] for r in gf_rows)
    systems = [
        dict(system="Chickasaw Nation shared WordPress theme (`chickasaw`)",
             platform_id="chickasaw_wscp_casino_game",
             hosts="www.winstar.com; www.riverwind.com; www.newcastlecasino.com",
             entry_point="/gaming/casino-games/list/  (nav label 'Game Finder')",
             transport="server-rendered HTML archive of custom post type "
                       "`wscp_casino_game`; 20 per page; `?page=N`; "
                       "`data-max-pages` printed in the Load More control; "
                       "taxonomies `wscp_casino_game_category` "
                       "(electronic-games / table-games / off-track-betting) "
                       "and `wscp_casino_game_venue`",
             fields_published="game title; manufacturer; one or more "
                              "denominations; venue (named gaming plaza / "
                              "lounge / salon); a map id linking to "
                              "/casino-map/?game-id=g<32 hex>",
             quantity_published="NO",
             row_means="one (title x denomination x venue) listing",
             row_is_a_cabinet="NO - the same title and manufacturer is listed "
                              "once per denomination, each with its own map id; "
                              "e.g. '$$$ Fever!' by Castle Hill Gaming appears "
                              "at 25c and at $1 as two rows",
             operator_disclaimer="DISCLAIMER: Our Game Finder tool is as "
                                 "accurate as possible - but since we're "
                                 "constantly expanding, there may be "
                                 "differences or changes that aren't reflected "
                                 "here.",
             rest_api="disabled - /wp-json/ and ?rest_route= both return the "
                      "site's HTML, so there is no JSON route",
             access="unauthenticated GET; robots.txt allows everything",
             status="HARVESTED"),
        dict(system="Coushatta Slot Finder (bespoke PHP)",
             platform_id="coushatta_slot_search",
             hosts="www.coushattacasinoresort.com",
             entry_point="/gaming/slot-search/  (nav label 'Slot Finder')",
             transport="form posts criteria to an unauthenticated GET fragment "
                       "endpoint /ajax-slot-result.php resolved through the "
                       "page's <base href> to the site root; refuses an empty "
                       "query ('Please enter a slot name, denomination, or a "
                       "manufacturer'), so the harvest iterates the finder's "
                       "own published manufacturer list",
             fields_published="game title; manufacturer; denomination; type "
                              "(Poker / Reel / Video); VOLATILITY (High / "
                              "Medium-High / Medium / Medium-Low / Low); a "
                              "floor-plan marker at /slot-map.php?sid=N",
             quantity_published="NO",
             row_means="one (title x denomination) listing with its own map sid",
             row_is_a_cabinet="NO - e.g. 'Dancing Pots Mc Md Prog' by Bluberi "
                              "is listed at $0.01, $0.02, $0.05 and $0.10 as "
                              "four rows",
             operator_disclaimer="",
             rest_api="n/a",
             access="unauthenticated GET; robots.txt disallows /admin/, "
                    "/includes/, /php_class/, /press-resources/ and others, "
                    "none of which is the finder",
             status="HARVESTED"),
        dict(system="FireKeepers 'Find Your Game'",
             platform_id="firekeepers_ee_search",
             hosts="firekeeperscasino.com",
             entry_point="/casino/games/slots/slots-results/",
             transport="a legacy ExpressionEngine search form (ACT=2, XID CSRF "
                       "token, encrypted `meta` blob) embedded in a WordPress "
                       "page; METHOD=POST to a path that no longer exists "
                       "(http://firekeeperscasino.com/games/slots/slots-results, "
                       "without the /casino/ prefix). Its WordPress REST "
                       "namespace `fk/v1` publishes shows, restaurants and "
                       "promotions and NO games route.",
             fields_published="keyword search box only; no browsable listing "
                              "is served without a query",
             quantity_published="NO",
             row_means="n/a - not harvested",
             row_is_a_cabinet="n/a",
             operator_disclaimer="",
             rest_api="wp/v2 + fk/v1 available; neither exposes a games route",
             access="unauthenticated, but result retrieval requires replaying a "
                    "per-session CSRF token against a broken action path",
             status="FOUND, NOT HARVESTED - recorded rather than forced"),
    ]
    for s in systems:
        s["rows_harvested"] = str(sum(v for k, v in harvested.items()
                                      if k in s["hosts"]))
        s["retrieved_at"] = TODAY
        s["built_by_script"] = SCRIPT
    write_csv(os.path.join(CLEAN, "gaming_game_finder_systems.csv"), systems)

    # ---- refusals: no new facility ids, ever ----
    for r in obs + labor + gf_rows:
        assert (not r["facility_id"]) or r["facility_id"] in valid_ids, \
            "facility_id not in gaming_facilities.csv: %s" % r["facility_id"]

    write_csv(os.path.join(REVIEW,
                           "gaming_property_site_refused_%s.csv" % TODAY), refused)
    n1 = merge_dated(os.path.join(CLEAN, "gaming_property_site_observations.csv"),
                     obs, ["site_host", "facility_id", "metric", "source_url",
                           "value", "source_quote"], ["unit"], "GPS")
    n2 = merge_dated(os.path.join(CLEAN, "gaming_property_labor_demand.csv"),
                     labor, ["site_host", "facility_id", "provision_type",
                             "source_url", "source_quote"],
                     ["value", "unit"], "GPL")
    n3 = merge_dated(os.path.join(CLEAN, "gaming_game_finder_observations.csv"),
                     gf_rows, ["site_host", "game_title", "manufacturer",
                               "denomination", "floor_location", "game_category",
                               "source_game_id"],
                     ["volatility_as_published", "listing_unit"], "GFO")
    print("extract: site obs %d | labor %d | game finder %d" % (n1, n2, n3))
    summary = {
        "site_observations": n1, "labor_demand": n2, "game_finder": n3,
        "site_obs_by_metric": dict(Counter(r["metric"] for r in obs)),
        "site_obs_properties": len({r["facility_id"] for r in obs if r["facility_id"]}),
        "gf_properties": len({r["facility_id"] for r in gf_rows if r["facility_id"]}),
        "gf_distinct_titles": len({r["game_title"] for r in gf_rows}),
        "gf_distinct_manufacturers": len({r["manufacturer"] for r in gf_rows
                                          if r["manufacturer"]}),
        "labor_by_type": dict(Counter(r["provision_type"] for r in labor)),
        "built_date": TODAY,
    }
    # ---- codebook fragment (master codebook is never touched) ----
    CB = [
     ("07j_gaming_property_site_observations", "observation_id",
      "GPS-nnnnn. Append-only; a value that changes is a NEW row, never an edit."),
     ("07j_gaming_property_site_observations", "facility_id",
      "Existing Cedar property id (CCP-/VP-/TPL-). BLANK where the host serves "
      "several Cedar properties, which is a refusal to attribute, not a gap."),
     ("07j_gaming_property_site_observations", "measurement_type",
      "PROPERTY_REPORTED_COUNT throughout. The operator is reporting about "
      "itself; this is never a regulator count and never an ACTIVE_FLOOR_COUNT."),
     ("07j_gaming_property_site_observations", "as_of_date",
      "The RETRIEVAL date. Operators almost never date these claims, so the "
      "date says when the claim was on the page, not when it was counted."),
     ("07j_gaming_property_site_observations", "source_quote",
      "Verbatim window around the number, so a reader can see the sentence the "
      "value came out of."),
     ("07j_gaming_property_site_observations", "attribution_basis",
      "single_property_host / multi_property_host / hand_ruling. Nothing is "
      "snapped to a nearest property."),
     ("07k_gaming_property_labor_demand", "observation_class",
      "LABOR_DEMAND_STATEMENT. An open posting or a preference policy is "
      "labour DEMAND and is NEVER an employee count."),
     ("07k_gaming_property_labor_demand", "provision_type",
      "indian_preference / gaming_license_required / wage_floor / "
      "tribal_employment_rights."),
     ("07l_gaming_game_finder_observations", "measurement_type",
      "GAME_FINDER_OBSERVATION, which sits in "
      "cedar_domain.NEVER_PROMOTES_TO_ACTIVE. It can never become an "
      "ACTIVE_FLOOR_COUNT."),
     ("07l_gaming_game_finder_observations", "listing_unit",
      "What ONE ROW IS: a (title x denomination) listing. The same title and "
      "manufacturer appears once per denomination, so a row count is not a "
      "device count and must never be summed as one."),
     ("07l_gaming_game_finder_observations", "manufacturer",
      "VERBATIM as the operator prints it, including its own vendor shorthand "
      "(EVERI2, ATI, VGT, ASTG, Ainsworth/AW). Not normalised, because "
      "normalising would assert an identity the source does not."),
     ("07l_gaming_game_finder_observations", "floor_location",
      "BLANK on the Chickasaw platform: the venue dropdown is printed but the "
      "server ignores it (measured). Blank means the source does not place the "
      "game, never that the game is unplaced."),
     ("07l_gaming_game_finder_observations", "quantity_if_known",
      "Always blank so far. No public finder in this sweep publishes how many "
      "cabinets carry a title."),
    ]
    write_csv(os.path.join(CODEBOOK, "07j_gaming_property_sites.csv"),
              [dict(dataset=d, variable=v, type="", units="", pct_filled="",
                    n_rows="", published="", access_tier="", description=t,
                    generated=TODAY) for d, v, t in CB],
              ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
               "published", "access_tier", "description", "generated"])

    json.dump(summary, open(os.path.join(LOGS, "142_summary_%s.json" % TODAY),
                            "w", encoding="utf-8"), indent=1)
    print(json.dumps(summary, indent=1)[:2000])


# ===========================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", required=True,
                    choices=["discover", "crawl", "gamefinder", "extract"])
    ap.add_argument("--limit", type=int, default=10 ** 6)
    ap.add_argument("--minutes", type=float, default=30.0)
    ap.add_argument("--hosts", default="", help="comma-separated host filter")
    a = ap.parse_args()
    deadline = time.time() + a.minutes * 60
    if a.phase == "discover":
        phase_discover(a.limit, deadline)
    elif a.phase == "crawl":
        phase_crawl(a.limit, deadline)
    elif a.phase == "gamefinder":
        phase_gamefinder(a.limit, deadline,
                         set(h.strip() for h in a.hosts.split(",") if h.strip()))
    else:
        phase_extract()


if __name__ == "__main__":
    main()
