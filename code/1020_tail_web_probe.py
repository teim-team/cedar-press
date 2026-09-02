#!/usr/bin/env python3
"""
1020_tail_web_probe.py -- WORKSTREAM SHARD-N. THE COVERAGE TAIL.

    py -3 code/1020_tail_web_probe.py            # run the ladder
    py -3 code/1020_tail_web_probe.py verify     # exit 1 if an invariant breaks
    py -3 code/1020_tail_web_probe.py selftest   # prove verify fires on a
                                                 # synthetic violation
    py -3 code/1020_tail_web_probe.py doc        # rewrite the tail report

SLICE -- DERIVED, NEVER ENUMERATED
    Every `cedar_uid` in data/spine/cedar_identity_register.csv that appears in
    NO shard map other than this one. Measured 2026-09-02 as 139 entities:
    69 Native Hawaiian Organizations, 62 federally recognized tribes, 8
    individually Native-owned businesses. Sibling shards A-H and K own the
    1,416 entities they already touched; this file owns only what nobody
    reached, and it re-derives the set on every run so that a sibling landing
    mid-flight shrinks this slice instead of duplicating it.

WHY THIS FILE EXISTS
    docs/SHARD_COVERAGE.md splits coverage three ways -- has a URL, attempted
    and none found, untouched -- because only the third is a gap in our effort.
    The third column was 139 and stalled: the shards that could reach these
    entities had finished, and no shard's slice contained them. An entity in
    that column is indistinguishable from an entity with no web presence, and
    the whole point of the ledger is that those are different findings.

THE LADDER (docs/HIDDEN_DATA_TECHNIQUES.md; recorded per entity in `evidence`)
    R1  PUBLISHER-STATED, tribes. BIA Tribal Leaders Directory, the Indian
        Affairs ArcGIS FeatureServer behind bia.gov's directory, pulled whole
        (`where=1=1`) rather than one tribe at a time. It carries a `website`
        field. 602 records, 527 with a website. This is the authoritative
        answer for a federally recognized tribe and it outranks any search.
    R2  PUBLISHER-STATED, Native Hawaiian Organizations. The DOI Office of
        Native Hawaiian Relations NHO Notification List (April 2025), the same
        document the register minted these entities from. Every directory
        entry carries a `Website:` line, and 91 of them say **"None listed"** --
        which is the organisation's own statement to its own registrar that it
        has no website. That is the strongest possible evidence for a negative
        and it is the reason this shard can close NHOs honestly at all.
    R3  DOMAIN FROM A PUBLISHED EMAIL. The rung that recovered Klawock: an
        organisation with no listed website that publishes info@example.org
        has told you its domain. Free-mail hosts are excluded, and the derived
        host is fetched and name-checked before it is recorded.
    R4  IRS/990. ProPublica Nonprofit Explorer (no key). Establishes the
        organisation exists as a filing entity, and yields an EIN -- a first
        row for an entity that had none.
    R5  MACHINE-READABLE PROBE on any host found: /wp-json/wp/v2/{media,types,
        pages}, sitemap(_index).xml, /feed/, ld+json. **A negative from search
        alone is not a negative** -- an absence recorded without this is
        NOT_SEARCHED_MACHINE_READABLE, a different claim.
    R6  NONE_ESTABLISHED. Only after >= 3 named routes are recorded in
        `evidence`. `verify` enforces that; it is not a convention.
    R7  DOMAIN DERIVED FROM THE NAME. Last programmatic rung, reached only
        when everything publisher-stated came up empty, and the most
        dangerous one in the file -- its first version fabricated ten sites.
        A candidate is accepted ONLY when the page text carries EVERY
        distinctive token of the entity's name AND a marker that the page is
        that kind of organisation; the URL itself is never evidence; parking
        pages are detected by their boilerplate, not by length; and a
        single-word domain label is never guessed. `verify` invariant (6)
        enforces the first of those against the written rows.
    R8  HAND SEARCH, by legal name, common name and community name
        separately. Three tribes the mechanical ladder could not reach were
        one search each: a website-builder subdomain, a reservation-specific
        government site, and a registered domain serving a placeholder. The
        table is a source of CANDIDATES only -- every entry is fetched and
        name-checked at run time like any guess, and the search that worked
        is written into `evidence`.

THREE THINGS THAT ARE NOT "NO WEBSITE"
    `government_refused_robots`  the site exists and its robots.txt says
        `Disallow: /` to every agent (samishtribe.nsn.us). A publisher
        decision, refused by every route, and NOT our coverage gap.
    `government_blocked_bot_protection`  the site exists and answers 403 to a
        declared research UA and to full browser headers alike -- a JS
        anti-bot challenge (koinationsonoma.com) or an edge WAF
        (scottsvalley-nsn.gov). An access control; it stays unbypassed.
    `directory_profile`  somebody else's page about this entity.
    None of the three counts as the entity having a website, and none of them
    is `none_established`. Collapsing any of them into "no website" would
    report a refusal or a WAF as an absence.

WHAT COUNTS AS THE ENTITY'S OWN SITE
    Three of the URLs the BIA publishes for California rancherias point at
    caltribalfamilies.org and sctca.net -- consortium profile pages, not the
    tribe's site. Recording those as `government` would inflate the coverage
    number with other people's websites, which is the same defect as counting
    an untouched entity as one with no web presence. They are recorded as
    `directory_profile` and they do NOT count as the tribe having a site.

WHAT IT NEVER DOES
    No commits. No spine writes -- promoting a harvested URL to
    `entity_website` is an assertion and goes through 510. No minting, no
    repointing, no identity resolution. No `cedar_constellation_edges.csv`;
    resolution candidates are reported to the constellation agent.
    TERMS_STATED_RESTRICTIVE hosts are refused by every route including
    Wayback. robots.txt Disallow is a refusal. No admin/staging/login paths.

HOST DISCIPLINE
    One request at a time, 1.5 s per host / 0.7 s global, declared UA.
    robots.txt is fetched with THIS module's UA and handed to
    RobotFileParser.parse(); .read() is never called, because it fetches as
    Python-urllib and a host that 403s that UA then reads as disallow_all --
    the defect that produced 22 phantom blocks on 2026-09-01. An unreadable
    robots.txt is ALLOWED with the reason noted, so every refusal this file
    records is a real quoted Disallow.

FLUSH PER ENTITY
    Every row is appended and fsync'd as it is produced. Buffered shard maps
    nearly lost ~1,159 rows once.
"""
from __future__ import annotations

import csv
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, "data", "spine", "cedar_identity_register.csv")
MAP_DIR = os.path.join(ROOT, "data", "staging", "tribe_web_map")
WEBMAP = os.path.join(MAP_DIR, "shard_n.csv")
HARVEST = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_n")
RAW = os.path.join(HARVEST, "raw")
BIA_JSON = os.path.join(HARVEST, "bia_tld_full.json")
NHO_PDF = os.path.join(HARVEST, "nhol-complete-list-final-web.pdf")
NHO_JSON = os.path.join(HARVEST, "nhol_parsed.json")
TODAY = date.today().isoformat()

WEBMAP_COLS = ["cedar_uid", "canonical_name", "entity_class", "url_type",
               "url", "http_status", "checked_date", "evidence"]

UA = ("CedarPress-research/1.0 (tribal entity web mapping; contact "
      "elijahsamsonmoreno@gmail.com)")

BIA_TLD = ("https://services1.arcgis.com/UxqqIfhng71wUT9x/arcgis/rest/"
           "services/TribalLeadership_Directory/FeatureServer/0/query")
NHO_PDF_URL = ("https://www.doi.gov/sites/default/files/documents/2025-04/"
               "nhol-complete-list-final-web.pdf")
PP_SEARCH = "https://projects.propublica.org/nonprofits/api/v2/search.json"

# A TERMS RESTRICTION ATTACHES TO A HOST, NOT TO A NATION.
#
# This file previously matched TERMS_STATED_RESTRICTIVE on the ENTITY NAME as
# well as the host, with tokens like "colville" and "nana". Cedar ruled on
# 2026-09-02 (docs/PUBLICATION_POLICY.md, TERMS-SCOPE) that a restriction
# attaches to the host and path where the terms were found and does NOT
# propagate to a nation's other hosts -- one restricted Navajo page had been
# excluding four Navajo casinos on unrelated domains. Name matching is that
# defect by construction, and "nana" as a substring would also have caught
# `Nanakuli`, `Hanapepe` and any other name containing those four letters.
#
# So: hosts only. The eight hard-listed SOURCES are unchanged and remain
# refused by every route including Wayback; what changes is that the refusal
# no longer follows the entity onto domains whose publisher stated nothing.
TERMS_RESTRICTED_HOSTS = (
    "colvilletribes.com", "ctuir.org", "umatilla.nsn.us", "yakama.com",
    "yakamanation-nsn.gov", "chickasaw.net", "nana.com", "akima.com",
    "southernute-nsn.gov", "southern-ute.nsn.us", "fcpotawatomi.com",
    "stillaguamish.com", "navajoeconomy.org",
    # Named-agent robots refusals found by the vendor-list registry
    # (review/tribal_vendor_list_registry_2026-08-26.csv): both carry
    # `User-agent: ClaudeBot / Disallow: /`. The live robots check above now
    # catches these on its own; they are listed so the refusal survives a
    # robots.txt that stops being readable.
    "penobscotnation.org", "elyshoshonetribe.com",
)

# Free-mail hosts carry no organisational domain. Deriving a site from one
# would map an entity onto Google.
FREEMAIL = {"gmail.com", "yahoo.com", "hotmail.com", "aol.com", "outlook.com",
            "icloud.com", "me.com", "msn.com", "comcast.net", "live.com",
            "hawaii.rr.com", "hawaiiantel.net", "mac.com", "protonmail.com",
            "att.net", "sbcglobal.net", "verizon.net", "earthlink.net",
            "juno.com", "yahoo.co.jp", "ymail.com", "gmail.com.", "aol.co.uk"}

_last_host: dict = {}
_last_any = [0.0]
_robots: dict = {}


# ------------------------------------------------------------------ fetch
def _sleep_for(host):
    now = time.time()
    d = max(1.5 - (now - _last_host.get(host, 0.0)),
            0.7 - (now - _last_any[0]), 0.0)
    if d > 0:
        time.sleep(d)


def _write_raw(name, text):
    os.makedirs(RAW, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:150]
    with open(os.path.join(RAW, safe), "w", encoding="utf-8") as fh:
        fh.write(text)


def restricted(url: str) -> bool:
    """Host-scoped only. See TERMS_RESTRICTED_HOSTS for why not by name."""
    h = urllib.parse.urlsplit(url if "//" in (url or "") else "//" + (url or "")).netloc.lower()
    h = h.split(":")[0]
    h = h[4:] if h.startswith("www.") else h
    if not h:
        return False
    return any(h == d or h.endswith("." + d) for d in TERMS_RESTRICTED_HOSTS)


# WE ARE CLAUDE, AND A HOST THAT NAMES CLAUDE IS TALKING TO US.
#
# `robots_ok` asked `can_fetch("CedarPress-research/1.0 ...", url)`. Two hosts
# in this shard's own slice -- `penobscotnation.org` and
# `elyshoshonetribe.com` -- carry `User-agent: ClaudeBot / Disallow: /`
# (Penobscot alongside a permissive `User-agent: *` block, Ely Shoshone naming
# `anthropic-ai` too). RobotFileParser matched the permissive wildcard block,
# because our UA string contains none of those tokens, and returned ALLOWED.
# Both were fetched.
#
# A named-agent rule is MORE SPECIFIC than the wildcard and therefore governs
# us -- Cedar had already ruled exactly that on these two hosts on 2026-08-26
# and excluded them from Wayback for the same reason. Declaring a custom UA is
# a courtesy; it is not a way to not be the agent the publisher refused. The
# check now evaluates every token that denotes this agent and takes the most
# restrictive answer.
#
# This is the third member of the family in this file: the Samish redirect
# (permission checked on the host we asked, bytes taken from the host that
# said no) and the circular name evidence. Each was a check that ran, passed,
# and was not measuring the thing its name claims.
AGENT_TOKENS = ("ClaudeBot", "anthropic-ai", "Claude-User", "Claude-SearchBot",
                "Claude-Web")


def robots_ok(url):
    """(allowed, note). Unreadable robots.txt -> ALLOWED, reason noted.

    Evaluated for our declared UA AND for every token that means "Claude".
    The most restrictive answer wins, and the token that refused is named.
    """
    p = urllib.parse.urlsplit(url)
    base = p.scheme + "://" + p.netloc
    if base not in _robots:
        try:
            _sleep_for(p.netloc)
            req = urllib.request.Request(base + "/robots.txt",
                                         headers={"User-Agent": UA})
            body = urllib.request.urlopen(req, timeout=25).read()
            body = body.decode("utf-8", "replace")
            _last_host[p.netloc] = _last_any[0] = time.time()
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(body.splitlines())
            _robots[base] = rp
        except Exception as e:                                    # noqa: BLE001
            _robots[base] = ("ERR", type(e).__name__)
    r = _robots[base]
    if isinstance(r, tuple):
        return True, "robots.txt unreadable (" + r[1] + ")"
    for tok in (UA,) + AGENT_TOKENS:
        if not r.can_fetch(tok, url):
            who = "our declared UA" if tok == UA else tok
            return False, "robots.txt Disallow for " + who
    return True, ""


BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Upgrade-Insecure-Requests": "1",
}


def fetch(url, timeout=30, respect_robots=True, browser_headers=False,
          relaxed_tls=False, save_as=None):
    """-> dict(status, text, final_url, error). Never raises.

    browser_headers and relaxed_tls are RECOVERY rungs. A 403 to a declared
    research UA is usually a stock-UA filter, and a handshake failure is a
    server config -- neither is an access control. A robots Disallow, a login
    wall and a TERMS_STATED_RESTRICTIVE source stay refused by every route.
    """
    if restricted(url):
        return {"status": "REFUSED_TERMS_STATED_RESTRICTIVE", "text": "",
                "final_url": url, "error": "publisher terms"}
    p = urllib.parse.urlsplit(url)
    if respect_robots:
        ok, rnote = robots_ok(url)
        if not ok:
            return {"status": "REFUSED_ROBOTS_DISALLOW", "text": "",
                    "final_url": url, "error": rnote or "robots.txt Disallow"}
    _sleep_for(p.netloc)
    hdrs = dict(BROWSER_HEADERS) if browser_headers else {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
        "Accept-Language": "en-US,en;q=0.9"}
    ctx = None
    if relaxed_tls:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    out = {"status": None, "text": "", "final_url": url, "error": ""}
    try:
        req = urllib.request.Request(url, headers=hdrs)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read(4_000_000)
            out["status"] = resp.status
            out["final_url"] = resp.geturl()
            ct = resp.headers.get("Content-Type", "") or ""
            enc = "utf-8"
            m = re.search(r"charset=([\w-]+)", ct)
            if m:
                enc = m.group(1)
            if "pdf" not in ct.lower():
                out["text"] = raw.decode(enc, "replace")
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        out["error"] = "HTTP " + str(e.code)
        try:
            out["text"] = e.read(200_000).decode("utf-8", "replace")
        except Exception:                                         # noqa: BLE001
            pass
    except Exception as e:                                        # noqa: BLE001
        out["status"] = "conn_error"
        out["error"] = type(e).__name__ + ": " + str(e)[:120]
    finally:
        _last_host[p.netloc] = _last_any[0] = time.time()
    # A REDIRECT CAN LAND ON A HOST THAT REFUSED US.
    # `samishindiannation.org` has no robots.txt objection and 301s to
    # `www.samishtribe.nsn.us`, whose robots.txt is `User-agent: * /
    # Disallow: /`. The robots check ran against the host we ASKED FOR and
    # passed; the body we received came from the host that had said no. That
    # is not a technicality -- the Samish Indian Nation stated a refusal and
    # this file recorded 200 and kept the page.
    #
    # The permission belongs to the host that serves the bytes, so it is
    # re-checked there and the body is discarded if it was not granted. This
    # is the same failure family as the robots false-block that cost a
    # sibling shard 22 hosts, in the opposite and worse direction: that one
    # refused an open site, this one read a closed one.
    if respect_robots and out.get("final_url") \
            and urllib.parse.urlsplit(out["final_url"]).netloc != p.netloc:
        ok2, _n2 = robots_ok(out["final_url"])
        if not ok2 or restricted(out["final_url"]):
            return {"status": "REFUSED_ROBOTS_DISALLOW_AFTER_REDIRECT",
                    "text": "", "final_url": out["final_url"],
                    "error": "redirected to " + out["final_url"]
                             + " whose robots.txt disallows us; body "
                               "discarded, not parsed, not cached"}
    if save_as and out.get("text"):
        _write_raw(save_as, out["text"])
    return out


def fetch_with_recovery(url, save_as=None):
    """Plain -> browser headers -> relaxed TLS. Records which rung worked."""
    r = fetch(url, save_as=save_as)
    if isinstance(r["status"], int) and 200 <= r["status"] < 400:
        r["rung"] = "plain"
        return r
    if r["status"] in ("REFUSED_ROBOTS_DISALLOW",
                       "REFUSED_TERMS_STATED_RESTRICTIVE"):
        r["rung"] = "refused"
        return r
    if r["status"] == 403:
        r2 = fetch(url, browser_headers=True, save_as=save_as)
        if isinstance(r2["status"], int) and 200 <= r2["status"] < 400:
            r2["rung"] = "browser_headers"
            return r2
    if r["status"] == "conn_error" and url.startswith("https"):
        r3 = fetch(url, relaxed_tls=True, save_as=save_as)
        if isinstance(r3["status"], int) and 200 <= r3["status"] < 400:
            r3["rung"] = "relaxed_tls"
            return r3
    r["rung"] = "failed"
    return r


# ------------------------------------------------------------------ text
TAG = re.compile(r"<[^>]+>")


def text_of(html):
    h = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    h = TAG.sub(" ", h)
    h = h.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#039;", "'")
    return re.sub(r"\s+", " ", h).strip()


def title_of(html):
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    return text_of(m.group(1))[:200] if m else ""


STOP = {"the", "of", "and", "a", "an", "inc", "llc", "tribe", "tribes",
        "nation", "band", "indian", "indians", "community", "association",
        "foundation", "group", "council", "corporation", "organization",
        "ohana", "hawaiian", "native", "company", "services", "llp"}


def tokens(name):
    s = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    return [t for t in s.split() if len(t) > 2 and t not in STOP]


def name_evidence(name, html, url=""):
    """Does this PAGE belong to this entity? -> (hits, n_tokens).

    THE URL IS THE GUESS. IT IS NEVER THE EVIDENCE.
    The first version put `url` in the haystack, and every derived candidate
    then matched itself: `capitan.org` "proved" it was the Capitan Grande
    Band because the string `capitan` was in the URL being tested. On that
    reasoning it accepted `fort.org` (a Gandi parking page), `grindstone.org`
    and `laguna.org` (both blank), `biglagoon.org` (an elementary school) and
    `cherokee.gov` -- the Cherokee Nation's own site -- as the website of a
    company called Cherokee Unlimited, Inc.

    Circular evidence is not weak evidence, it is no evidence, and it
    produced the one outcome this project forbids outright: ten fabricated
    rows, each of which would have read as a closed coverage gap. They were
    caught by reading the titles of what had been accepted, which is the
    check that should have been in the code. The `url` parameter is kept so
    callers need not change, and is deliberately unused.
    """
    del url                     # see above: the guess is never the evidence
    toks = tokens(_deaccent(name))
    if not toks:
        return 0, 0
    hay = _deaccent(text_of(html)[:60_000]).lower()
    return sum(1 for t in toks if t in hay), len(toks)


# A registrar parking page is a 200 with plenty of text, none of it the
# entity's. `fort.org` served 1.5 KB of Gandi boilerplate and sailed past a
# "is there enough text on this page" test.
#
# SPLIT INTO STRONG AND WEAK, BECAUSE THE FIRST VERSION FAILED THE OTHER WAY.
# One regex containing "coming soon" flagged the Quileute Tribe's live site as
# parked: the front page announces "Quileute Days is coming soon!" A detector
# that turns a working tribal website into "no web presence" is the same
# false-absence defect as the one it was written to prevent, pointing the
# other way. Strong phrases are things only a parking page says. Weak ones are
# things a real page says too, so they count only on a page with almost no
# content of its own.
PARKED_STRONG = re.compile(
    r"(?i)(this domain (name )?(has been |is )?(registered|for sale|parked)"
    r"|domain (name )?is (for sale|available|parked)"
    r"|buy this domain|domain parking|parked (free )?courtesy of"
    r"|registered (with|at) (gandi|godaddy|namecheap|sedo)"
    r"|default web site page|apache2? ubuntu default"
    r"|welcome to nginx)")
PARKED_WEAK = re.compile(
    r"(?i)(future home of|coming soon|under construction|site is being "
    r"(built|redesigned)|placeholder)")


def is_parked(body, title):
    """Strong markers anywhere; weak markers only on a near-empty page."""
    head = (body or "")[:4000]
    if PARKED_STRONG.search(head) or PARKED_STRONG.search(title or ""):
        return True
    return len(body or "") < 1200 and bool(PARKED_WEAK.search(head))


# A 200 THAT IS A BOT CHALLENGE IS NOT THE SITE.
# Two of the 51 tribal sites accepted on pass 1 -- Potter Valley Tribe and the
# Paiute Indian Tribe of Utah -- returned HTTP 200 and 169 bytes of SiteGround
# captcha redirect. Green status code, valid HTML, and not one byte of the
# tribe's website. This is the same shape as the `?wpdmdl=` incident in
# HIDDEN_DATA_TECHNIQUES: a check that passed for the wrong reason and would
# have shipped. The site exists, so the honest record is
# `government_blocked_bot_protection`, not `government` and not an absence.
CHALLENGE = re.compile(
    r"(?i)(sgcaptcha|cf-browser-verification|cf_chl|challenge-platform"
    r"|just a moment\.\.\.|checking your browser|enable javascript and "
    r"cookies|ddos protection by|incapsula incident|access denied"
    r"|請開啟 javascript|attention required)")


def is_challenge(html):
    """True when a 200 body is an interstitial rather than the site."""
    head = html[:4000]
    return bool(CHALLENGE.search(head)) or (
        len(html) < 700 and "http-equiv=\"refresh\"" in head.lower()
        and "captcha" in head.lower())


# For the page to be THIS KIND of organisation, not merely a page that
# happens to contain the name.
CLASS_MARKERS = {
    "Federally recognized tribe": ("tribe", "tribal", "rancheria", "nation",
                                   "band", "reservation", "pueblo",
                                   "indian", "tribal council"),
    "Native Hawaiian Organization": ("hawaii", "hawaiian", "ohana", "kanaka",
                                     "homestead", "moku", "ahupua",
                                     "nonprofit", "non-profit", "kupuna"),
    "Individually Native-owned business": ("llc", " inc", "company",
                                           "our services", "about us",
                                           "contact us"),
}


def _deaccent(s):
    import unicodedata
    s = (s or "").replace("ʻ", "").replace("‘", "")
    s = s.replace("’", "").replace("́", "")
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


# ------------------------------------------------------- machine-readable
RUNGS = [
    ("wp_media", "/wp-json/wp/v2/media?per_page=1&_fields=id"),
    ("wp_types", "/wp-json/wp/v2/types"),
    ("wp_pages", "/wp-json/wp/v2/pages?per_page=1&_fields=id,link"),
    ("sitemap_index", "/sitemap_index.xml"),
    ("sitemap", "/sitemap.xml"),
    ("feed", "/feed/"),
]


def probe_machine_readable(base_url, tag):
    """docs/HIDDEN_DATA_TECHNIQUES.md: a negative from search alone is not
    evidence. Until this has run against a host, 'nothing published' is
    NOT_SEARCHED_MACHINE_READABLE. <= 6 cheap requests."""
    p = urllib.parse.urlsplit(base_url)
    base = p.scheme + "://" + p.netloc
    got, other = [], []
    for rung, path in RUNGS:
        r = fetch(base + path, timeout=25,
                  save_as=tag + "__" + rung if tag else None)
        st = r["status"]
        if isinstance(st, int) and st == 200 and r["text"].strip():
            n = ""
            if rung.startswith("wp_"):
                try:
                    j = json.loads(r["text"])
                    n = "/" + str(len(j)) if isinstance(j, list) else ""
                except ValueError:
                    continue
            got.append(rung + ":200" + n)
        elif st != 404:
            other.append(rung + ":" + str(st))
    # AN ANSWER THAT IS A REFUSAL IS NOT AN OPEN SURFACE.
    # Samish's row read `machine_readable_surface ... 200` with every rung
    # recorded as REFUSED_ROBOTS_DISALLOW inside it. Non-200 outcomes are
    # still worth keeping -- they say what was tried -- but only alongside a
    # rung that actually answered.
    return got + other if got else []


# ------------------------------------------------------------- registers
def read_register():
    with open(REGISTER, encoding="utf-8-sig", errors="replace",
              newline="") as fh:
        return list(csv.DictReader(fh))


def touched_elsewhere():
    """uids any OTHER shard map has a row for. Derived from disk, never a
    hard-coded roster -- 528 lost sight of shard K for exactly that reason."""
    out = set()
    if not os.path.isdir(MAP_DIR):
        return out
    for fn in sorted(os.listdir(MAP_DIR)):
        if not fn.startswith("shard_") or not fn.endswith(".csv"):
            continue
        if fn == os.path.basename(WEBMAP):
            continue
        with open(os.path.join(MAP_DIR, fn), encoding="utf-8-sig",
                  errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                u = (r.get("cedar_uid") or "").strip()
                if u:
                    out.add(u)
    return out


def slice_rows():
    done = touched_elsewhere()
    return [r for r in read_register()
            if r.get("cedar_uid") and r["cedar_uid"] not in done]


# --------------------------------------------------------------- writers
def ensure_webmap():
    os.makedirs(MAP_DIR, exist_ok=True)
    if not os.path.exists(WEBMAP) or os.path.getsize(WEBMAP) == 0:
        with open(WEBMAP, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerow(WEBMAP_COLS)


def add_row(uid, name, cls, url_type, url, status, evidence):
    """Append ONE row and fsync. Never buffer -- a buffered shard map nearly
    lost ~1,159 rows on this project once."""
    ensure_webmap()
    with open(WEBMAP, "a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow([uid, name, cls, url_type, url, status,
                                 TODAY, evidence])
        fh.flush()
        os.fsync(fh.fileno())


def already_done():
    if not os.path.exists(WEBMAP):
        return set()
    with open(WEBMAP, encoding="utf-8-sig", errors="replace",
              newline="") as fh:
        return {(r.get("cedar_uid") or "").strip()
                for r in csv.DictReader(fh)}


# ------------------------------------------------------------- R1 BIA TLD
def load_bia():
    if os.path.exists(BIA_JSON):
        with open(BIA_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    out, off = [], 0
    while True:
        u = (BIA_TLD + "?where=1%3D1&outFields=*&returnGeometry=false&f=json"
             "&resultOffset=" + str(off) + "&resultRecordCount=1000")
        r = fetch(u, timeout=90, respect_robots=False)
        if not isinstance(r["status"], int) or r["status"] != 200:
            break
        d = json.loads(r["text"])
        f = d.get("features", [])
        out += [x["attributes"] for x in f]
        if not d.get("exceededTransferLimit") or not f:
            break
        off += len(f)
    os.makedirs(HARVEST, exist_ok=True)
    with open(BIA_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    return out


DROP = (r"\b(the|of|indian|indians|tribe|tribes|band|bands|nation|nations|"
        r"community|communities|rancheria|reservation|pueblo|colony|group|inc|"
        r"california|nevada|arizona|utah|oregon|washington|montana|oklahoma|"
        r"maine|virginia|new mexico|south dakota|north dakota|minnesota|"
        r"michigan|wisconsin|and)\b")


def bia_norm(s):
    s = (s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", _deaccent(s))
    s = re.sub(DROP, " ", s)
    return re.sub(r"\s+", " ", s).strip()


def bia_index(bia):
    idx = {}
    for b in bia:
        for k in ("tribefullname", "tribe", "tribealternatename"):
            v = bia_norm(b.get(k))
            if v:
                idx.setdefault(v, b)
    return idx


def bia_lookup(row, idx):
    for cand in (row.get("federal_register_legal_name"),
                 row.get("canonical_name")):
        n = bia_norm(cand)
        if n and n in idx:
            return idx[n], "exact on '" + (cand or "") + "'"
    n = bia_norm(row.get("federal_register_legal_name")
                 or row.get("canonical_name"))
    if len(n) > 6:
        for k, v in idx.items():
            if n in k or k in n:
                return v, "substring on '" + k + "'"
    return None, ""


# ------------------------------------------------------------- R2 DOI NHO
def load_nho():
    """Parse the DOI ONHR NHO Notification List into name -> {website, emails}.

    The document is the register's own source for these entities, and its
    `Website:` line is the ORGANISATION'S OWN STATEMENT to its registrar.
    'None listed' from that field is a publisher-stated absence, not our
    failure to find something -- which is the distinction this whole shard
    exists to keep.
    """
    if os.path.exists(NHO_JSON):
        with open(NHO_JSON, encoding="utf-8") as fh:
            return json.load(fh)
    if not os.path.exists(NHO_PDF):
        r = fetch(NHO_PDF_URL, timeout=120)
        if not isinstance(r["status"], int):
            return {}
    try:
        import fitz
    except ImportError:
        return {}
    doc = fitz.open(NHO_PDF)
    full = "\n".join(doc[p].get_text() for p in range(doc.page_count))
    _write_raw("nhol_text.txt", full)
    lines = [ln.strip() for ln in full.split("\n")]

    # ANCHOR ON THE DOCUMENT'S OWN CONTENTS, NOT ON A LAYOUT GUESS.
    # The first cut took "the line above `Established:`" as the organisation
    # name. That is right for most entries and wrong for every entry whose
    # predecessor's summary ran to the page foot -- it produced names like
    # "imbued with the spirit of ʻIʻo." A wrong key here does not error, it
    # just fails to match a register entity and silently understates coverage,
    # which is the class of defect this shard exists to fix. The contents
    # pages list all 178 headings verbatim; each is then located as a
    # standalone line in the body and the entry runs to the next heading.
    toc = [a.strip() for a, _ in
           # The space before the dot leader is OPTIONAL. Requiring it dropped
           # 'Au Puni O Hawaiʻi....' and 'Kaʻuikiokapō....' -- both present in
           # the document, both invisible to the parser, both then reported as
           # "no DOI entry" for a register entity that has one.
           re.findall(r"^(.+?)\s*\.{4,}\s*(\d+)\s*$", full, re.M)]
    key = {}
    for name in toc:
        key[_flat(name)] = name
    first = next((i for i, ln in enumerate(lines) if ln == "Established:"), 0)
    at = {}
    for i, ln in enumerate(lines):
        if i < first - 8:
            continue
        k = _flat(ln)
        if k and k in key and k not in at:
            at[k] = i
    order = sorted(at.items(), key=lambda kv: kv[1])
    out = {}
    for n, (k, i) in enumerate(order):
        end = order[n + 1][1] if n + 1 < len(order) else len(lines)
        block = "\n".join(lines[i:end])
        site = ""
        raw_site = ""
        m = re.search(r"Website:\s*\n?\s*(\S[^\n]*)", block)
        if m:
            v = m.group(1).strip()
            raw_site = v
            # THE FIELD IS FREE TEXT AND ORGANISATIONS WRITE PROSE IN IT.
            # Two entries say "Under Construction" and "Pending". Taken
            # literally the parser produced `https://Under Construction` and
            # `https://Pending` and filed them as the organisation's website.
            # A value only counts as a website if it looks like a host.
            if re.match(r"^(https?://)?[A-Za-z0-9][A-Za-z0-9.-]*\.[A-Za-z]{2,}",
                        v):
                site = v
        mails = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
                           block)
        out[key[k]] = {"website": site, "website_field_text": raw_site,
                       "emails": sorted(set(mails)),
                       "website_field_present": bool(m),
                       "website_none_listed": bool(m) and not site}
    with open(NHO_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    return out


def _flat(s):
    """Diacritic- and punctuation-free key. 'Laʻiʻōpua' and 'Laiopua' are one
    word; the ʻokina and kahakō are the reason a plain string compare misses
    most of this document."""
    return re.sub(r"[^a-z0-9]", "", _deaccent(s).lower())


def nho_norm(s):
    s = _deaccent(s or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def nho_lookup(name, nho):
    key = nho_norm(name)
    idx = {nho_norm(k): (k, v) for k, v in nho.items()}
    if key in idx:
        return idx[key]
    for k, kv in idx.items():
        if key and (key in k or k in key) and abs(len(k) - len(key)) < 14:
            return kv
    return None, None


# --------------------------------------------------------- R3 email domain
# A SHARED INSTITUTIONAL DOMAIN IS NOT THE ORGANISATION'S DOMAIN.
# One ohana lists a contact at `@hawaii.edu`, and R3 dutifully fetched the
# University of Hawaii. A volunteer's work address says where that person
# works, not who the organisation is, and mapping an entity onto its
# volunteer's employer is a misattribution with a 108 KB homepage attached.
SHARED_TLD = (".edu", ".gov", ".mil", ".us")


def domains_from_emails(emails):
    out = []
    for e in emails:
        d = e.split("@")[-1].lower().strip(". ")
        if not d or "." not in d or d in FREEMAIL or d in out:
            continue
        if d.endswith(SHARED_TLD):
            continue
        out.append(d)
    return out


# ------------------------------------------------------------ R4 990/IRS
def propublica(name, state=""):
    """IRS filer lookup. ALL of the name's distinctive tokens, or nothing.

    THE FIRST RULE HERE WAS `len(want & got) >= len(want) - 1`, AND IT
    ATTRIBUTED SIX FILERS TO THE WRONG ORGANISATION:

        Cherokee Unlimited, Inc   ->  DUCKS UNLIMITED INC, Memphis TN
        Samish Indian Nation      ->  Samish Montessori School
        Koi Nation of N. Calif.   ->  Koi Heart, New Orleans LA
        Fort Bidwell Indian Comm. ->  Fort Bidwell Volunteer Fire Department
        Grindstone Rancheria      ->  Grindstone Association, Winter Harbor ME
        Potter Valley Tribe       ->  Potter Valley Cemetery Auxiliary

    "n-1 of the tokens" means a two-word name matches on ONE word, and one
    word is a place name or a common adjective. An EIN on the wrong entity is
    the same defect as a URL on the wrong entity, and harder to spot because
    an EIN looks like a fact.

    Two changes. Every distinctive token must be present, and the filer's
    state must not contradict the register's -- and see the caller: this
    route no longer runs for federally recognized tribes at all, because a
    tribe is not a 501(c)(3) and everything that matched one was a local
    organisation sharing the place name.
    """
    q = urllib.parse.urlencode({"q": name})
    r = fetch(PP_SEARCH + "?" + q, timeout=40, respect_robots=False)
    if not isinstance(r["status"], int) or r["status"] != 200:
        # 404 is this API's empty-search answer, not a transport failure.
        if r["status"] == 404:
            return None, "propublica:zero_results(404 is its empty search)"
        return None, "propublica:" + str(r["status"])
    try:
        d = json.loads(r["text"])
    except ValueError:
        return None, "propublica:unparseable"
    orgs = d.get("organizations") or []
    if not orgs:
        return None, "propublica:0_results"
    want = set(tokens(_deaccent(name)))
    if not want:
        return None, "propublica:no distinctive tokens in the entity name"
    for o in orgs:
        got = set(tokens(_deaccent(o.get("name", ""))))
        if not want.issubset(got):
            continue
        ost = (o.get("state") or "").upper()
        if state and ost and ost != state.upper():
            continue
        return o, ("propublica:matched on ALL of " + ",".join(sorted(want))
                   + "; filer state " + (ost or "?"))
    return None, ("propublica:" + str(len(orgs))
                  + "_results, none carried every token of "
                  + ",".join(sorted(want)))


# ------------------------------------------------------------------ shape
DOMAIN_WORDS = {"the", "of", "and", "a", "an", "inc", "llc", "indians",
                "california", "nevada", "arizona", "utah", "oregon",
                "washington", "montana", "oklahoma", "maine", "virginia",
                "mexico", "new", "dakota", "south", "north", "minnesota",
                "michigan", "wisconsin", "carolina", "island", "rhode",
                "massachusetts", "york", "previously", "listed", "as"}


def candidate_hosts(row):
    """Guess the domain from the name -- R7, the last programmatic rung.

    Deliberately narrow: a handful of shapes per tribe, each of which must
    then survive `try_host`'s name test before it is written. Tribal
    governments cluster hard on `.nsn.gov`, `-nsn.gov`, `.nsn.us` and plain
    `.org`, so the shapes are not arbitrary; they are the observed pattern in
    the 527 websites the BIA directory already publishes.

    A guess that answers 200 and does NOT carry the tribe's name is recorded
    as unverified or discarded, never as the tribe's site.
    """
    src = []
    for f in ("canonical_name", "federal_register_legal_name"):
        v = row.get(f) or ""
        v = re.sub(r"\(.*?\)", " ", v)
        v = re.sub(r"[^A-Za-z0-9 ]", " ", _deaccent(v)).lower()
        t = [x for x in v.split()
             if x and x not in DOMAIN_WORDS and len(x) > 1]
        if t:
            src.append(t)
    stems = []
    for t in src:
        core = [x for x in t if x not in
                ("tribe", "tribes", "band", "bands", "nation", "nations",
                 "indian", "community", "rancheria", "reservation", "pueblo",
                 "colony", "group", "town")]
        # A ONE-WORD STEM IS SOMEBODY ELSE'S DOMAIN.
        # `core[:1]` generated fort, capitan, grindstone, laguna, cherokee and
        # sanjuan. Every one of those domains belongs to another party, and
        # every one was accepted. A guess is only worth sending when the label
        # carries enough of the name to be improbable by chance: two joined
        # tokens, or a single long one.
        cands = {"".join(t), "".join(core), "".join(core[:2])}
        if len(core) == 1 and len(core[0]) >= 9:
            cands.add(core[0])
        for base in (cands - {""}):
            if 9 <= len(base) <= 30 and base not in stems:
                stems.append(base)
    out = []
    for b in stems[:4]:
        # `.net` earned its place: Guidiville Rancheria publishes
        # admin@guidiville.net and the first suffix list would never have
        # tried it.
        for suf in (".org", "-nsn.gov", ".nsn.gov", ".com", ".nsn.us",
                    ".net"):
            h = b + suf
            if h not in out:
                out.append(h)
    return out[:12]


# ---------------------------------------------------------------- R8
# HAND SEARCH, BY EVERY NAME THE ENTITY GOES BY. RECORDED, NOT ASSERTED.
#
# The rungs above are all mechanical, and mechanical rungs cannot reach a
# tribal site hosted on a website-builder subdomain or one whose domain bears
# no resemblance to the tribe's name. Three of the eleven tribes the automated
# ladder could not close were reachable in one search each -- searching the
# legal name, the common name and the community name separately, which is the
# rung docs/HIDDEN_DATA_TECHNIQUES.md calls for and which no regex performs.
#
# EVERY ENTRY HERE IS STILL FETCHED AND NAME-CHECKED AT RUN TIME by the same
# `try_host` the guesses go through. This table supplies the candidate; it does
# not supply the verdict. A URL that stops working, starts serving a challenge
# or fails the name test is recorded that way on the next run, and nothing
# here is exempt from `verify`.
#
# `how` is written into `evidence` so the next agent knows the search that
# worked, and a customer asking where the URL came from gets a real answer.
R8_HAND_SEARCH = {
    # BIA `website` field EMPTY for all three.
    "CE-0015T-S3": {          # Kialegee Tribal Town
        "host": "kialegeetribal.yourwebsitespace.com",
        "how": "searched the legal name 'Kialegee Tribal Town' rather than a "
               "derived domain; the tribe's site is on a website-builder "
               "subdomain (formerly kialegeetribal.webstarts.com, which now "
               "301s here), a shape no domain guess can reach",
    },
    "CE-0018R-W1": {          # Passamaquoddy Tribe
        "host": "passamaquoddy.com",
        "how": "the Passamaquoddy Tribe governs at two reservations and the "
               "BIA directory lists no website; this is the Indian Township "
               "(Motahkomikuk) tribal government site. Sipayik's "
               "wabanaki.com and passamaquoddypeople.com both answer 200 "
               "with a bot challenge and are NOT recorded as reached",
    },
    # DOI "None listed" for this one; the site is live and carries the whole
    # name. The derivation rung could not reach it because the domain is the
    # short form `makuu.org` while the legal name has five words -- a
    # five-character label, below the floor a guess is allowed to use. The
    # neighbouring register entity, Makuʻu Farmers Association, is a DIFFERENT
    # organisation whose market this one hosts: makuufarmersassociation.org
    # does not resolve, and its "None listed" stands.
    "CE-000YG-PG": {          # ʻO Makuʻu Ke Kahua Community Center
        "host": "makuu.org",
        "how": "searched the community name 'Makuʻu' rather than the "
               "organisation's registered name -- the lesson of SEARCHING "
               "FOR THE INSTITUTION INSTEAD OF THE THING, applied to a "
               "domain label rather than to a programme",
    },
    # Guidiville publishes admin@guidiville.net, so the DOMAIN is
    # publisher-stated -- but the domain serves a Sonic.net "future home of"
    # placeholder. Included so the finding is "domain registered, no site
    # published" rather than a silent absence.
    "CE-0014V-TC": {          # Guidiville Rancheria
        "host": "guidiville.net",
        "how": "domain derived from admin@guidiville.net, the address the "
               "tribe publishes in the BIA and CNIGA directories",
    },
}


def try_host(host, name, tag, cls=""):
    """Fetch a candidate host and require the page to prove it is the entity's.

    Returns (url, status, verdict, note). A 200 is not enough: a derived
    domain frequently lands on a parking page or an unrelated business, and
    recording one of those as the entity's website is worse than recording
    nothing, because nothing is visible in the ledger and a wrong URL is not.
    """
    # RESOLVE BEFORE YOU KNOCK. Most derived candidates do not exist, and the
    # first version spent a robots.txt fetch plus a page fetch, then the same
    # two again for the www host -- four rate-limited HTTP requests to learn
    # what one DNS lookup answers in milliseconds. It made the sweep roughly
    # four times slower and put four times the load on other people's servers
    # to discover nothing.
    live = []
    for h in (host, "www." + host):
        try:
            socket.getaddrinfo(h, 443, proto=socket.IPPROTO_TCP)
            live.append(h)
        except OSError:
            continue
    if not live:
        return ("", "", "no_response",
                "DNS: neither " + host + " nor www." + host + " resolves")
    for scheme in ("https://", "http://"):
        for h in live:
            url = scheme + h
            r = fetch_with_recovery(url, save_as=tag)
            st = r["status"]
            if not (isinstance(st, int) and 200 <= st < 400):
                continue
            hits, ntok = name_evidence(name, r["text"])
            body = text_of(r["text"])
            title = title_of(r["text"])
            if is_parked(body, title):
                return (r["final_url"], st, "parked_domain",
                        "200 from a registrar parking or placeholder page: "
                        + title[:60])
            # A FRAMESET IS A SITE. Bridgeport Indian Colony serves a 1999-era
            # `<frameset>`: 752 bytes, 24 characters of text, and a real
            # website behind it. A pure length test calls that parked.
            frames = bool(re.search(r"(?i)<frame(set)?\b", r["text"]))
            if len(body) < 200 and not frames:
                return (r["final_url"], st, "parked_domain",
                        "200 with under 200 characters of text")
            # A NAME MADE ONLY OF STOPWORDS CANNOT BE IDENTITY-CHECKED FROM
            # PAGE TEXT, AND MUST NOT BE GUESSED AT.
            # The Alaska Native village of *Council* matched `kawerak.org` in a
            # sibling sweep and produced six junk rows: strip the generic words
            # and nothing distinctive is left, so "does this page name the
            # entity" has no content to test. Five register entities have this
            # shape -- Council, Council Native Corporation, Hawaiian Native
            # Corporation, Ho Ohana, ʻOhana Lo -- two of them in this slice.
            #
            # This file already refused them, but only as a side effect of
            # `if ntok and ...` being false. A safety that nobody wrote down is
            # a safety that the next edit removes, so it is now stated, given
            # its own verdict, and gated in `verify`.
            if not ntok:
                return (r["final_url"], st, "unverifiable_name",
                        "the entity's name is entirely generic words, so no "
                        "page-text identity check is possible; a derived or "
                        "guessed host can NEVER be accepted for this entity. "
                        "title=" + title[:70])
            marker = any(m in body.lower()[:20_000]
                         for m in CLASS_MARKERS.get(cls, ()))
            # ALL of the entity's distinctive tokens AND a class marker.
            # "half the tokens" is what let an elementary school through for
            # Big Lagoon Rancheria.
            if ntok and hits == ntok and marker:
                return (r["final_url"], st, "verified",
                        "name evidence " + str(hits) + "/" + str(ntok)
                        + " tokens ALL present in the page text, plus a "
                        + "class marker; title=" + title[:80]
                        + "; rung=" + r.get("rung", ""))
            return (r["final_url"], st, "unverified",
                    "200 but name evidence " + str(hits) + "/" + str(ntok)
                    + " tokens and class marker " + str(marker)
                    + "; title=" + title[:80]
                    + " -- NOT accepted as this entity's site")
    return ("", "", "no_response", "")


# ------------------------------------------------------------------- main
def run():
    reg_rows = slice_rows()
    done = already_done()
    todo = [r for r in reg_rows if r["cedar_uid"] not in done]
    print("  shard_n slice %d untouched entities, %d already written, "
          "%d to do" % (len(reg_rows), len(reg_rows) - len(todo), len(todo)))
    if not todo:
        return 0

    bia = bia_index(load_bia())
    nho = load_nho()
    print("  routes loaded: BIA TLD %d names, DOI NHO list %d entries"
          % (len(bia), len(nho)))

    n_url = n_none = n_open = 0
    for i, row in enumerate(todo, 1):
        uid = row["cedar_uid"]
        name = row.get("canonical_name", "")
        cls = row.get("entity_class", "")
        tried = []
        got_url = False
        wrote = [0]

        def emit(*args):
            wrote[0] += 1
            add_row(*args)


        # ---- R1 BIA Tribal Leaders Directory ----------------------------
        if cls == "Federally recognized tribe":
            b, how = bia_lookup(row, bia)
            if b:
                site = (b.get("website") or "").strip()
                tried.append("R1 BIA Tribal Leaders Directory ArcGIS "
                             "FeatureServer (" + how + ")")
                if site:
                    u = site if site.startswith("http") else "https://" + site
                    host = urllib.parse.urlsplit(u).netloc.lower()
                    third = ("caltribalfamilies.org" in host
                             or "sctca.net" in host)
                    r = fetch_with_recovery(u, save_as=uid + "__bia_site")
                    st = r["status"]
                    ok = isinstance(st, int) and 200 <= st < 400
                    if third:
                        ut = "directory_profile"
                        note = ("BIA publishes a consortium PROFILE PAGE for "
                                "this tribe, not a tribal site. Recorded as a "
                                "profile and NOT counted as the tribe having "
                                "a website.")
                    elif ok and is_challenge(r["text"]):
                        ut = "government_blocked_bot_protection"
                        note = ("HTTP " + str(st) + " but the body is a bot "
                                "challenge interstitial, not the site -- "
                                + str(len(r["text"])) + " bytes. A 200 is not "
                                "proof you fetched the right thing. The site "
                                "exists; we did not reach it.")
                        ok = False
                    elif ok:
                        ut, note = "government", ("verified 2xx, "
                                                  + str(len(r["text"]))
                                                  + " bytes of body")
                        got_url = True
                    elif st == "REFUSED_TERMS_STATED_RESTRICTIVE":
                        # NOT "did not answer". The publisher refused; we
                        # never asked. Filing a stated refusal as a technical
                        # failure misdescribes the nation's own decision.
                        ut = "TERMS_RESTRICTED_DO_NOT_HARVEST"
                        note = ("the site EXISTS and its publisher is "
                                "TERMS_STATED_RESTRICTIVE for this host. Not "
                                "fetched by any route, including Wayback. "
                                "Not an absence; a publisher decision.")
                    elif st == "REFUSED_ROBOTS_DISALLOW":
                        # A SITE THAT EXISTS AND HAS TOLD US NOT TO FETCH IT.
                        # samishtribe.nsn.us serves `User-Agent: * / Disallow:
                        # /`. That is not "no website" and it is not our
                        # effort gap -- it is the publisher's decision, and
                        # filing it as an absence would both understate
                        # coverage and misrepresent the nation.
                        ut = "government_refused_robots"
                        note = ("the site EXISTS and its robots.txt states "
                                "Disallow: / for all agents. Refused by every "
                                "route. Not an absence; a publisher decision.")
                    elif st == 403:
                        # Bot-protection, not an access control we may work
                        # around. koinationsonoma.com serves a JS challenge
                        # (sitedistrict) and scottsvalley-nsn.gov an Akamai
                        # 403, to browser headers as well as ours. The site
                        # exists; we could not fetch it politely.
                        ut = "government_blocked_bot_protection"
                        note = ("the site EXISTS; the host returns 403 to a "
                                "declared research UA AND to full browser "
                                "headers -- an anti-bot challenge, which is "
                                "an access control and stays unbypassed.")
                    else:
                        ut = "unverified_government"
                        note = ("BIA-published URL did not answer; recovery "
                                "rungs (browser headers, relaxed TLS) also "
                                "failed: " + str(r.get("error"))[:80])
                    emit(uid, name, cls, ut, r.get("final_url") or u, st,
                            "TRIED: " + " | ".join(tried) + " || " + note
                            + " || BIA record: " + (b.get("tribefullname")
                                                    or ""))
                    if ok and not third:
                        mr = probe_machine_readable(
                            r["final_url"], uid + "__mr")
                        if mr:
                            n_open += 1
                            emit(uid, name, cls, "machine_readable_surface",
                                    urllib.parse.urlsplit(
                                        r["final_url"]).scheme + "://"
                                    + urllib.parse.urlsplit(
                                        r["final_url"]).netloc,
                                    200,
                                    "TRIED: R5 machine-readable probe "
                                    "(HIDDEN_DATA_TECHNIQUES checklist) || "
                                    "open: " + ", ".join(mr))
                else:
                    tried.append("R1 returned a BIA record with an EMPTY "
                                 "website field ('" +
                                 (b.get("tribefullname") or "") + "')")
            else:
                tried.append("R1 BIA Tribal Leaders Directory: no record "
                             "matched this legal name")

        # ---- R2 DOI Office of Native Hawaiian Relations -----------------
        if not got_url and cls == "Native Hawaiian Organization":
            key, rec = nho_lookup(
                row.get("federal_register_legal_name") or name, nho)
            if rec is None:
                key, rec = nho_lookup(name, nho)
            if rec:
                tried.append("R2 DOI ONHR NHO Notification List, April 2025, "
                             "entry '" + key + "'")
                site = rec.get("website") or ""
                if site:
                    u = site if site.startswith("http") else "https://" + site
                    r = fetch_with_recovery(u, save_as=uid + "__doi_site")
                    st = r["status"]
                    ok = isinstance(st, int) and 200 <= st < 400
                    if ok and (is_challenge(r["text"])
                               or is_parked(text_of(r["text"]),
                                            title_of(r["text"]))
                               or (len(text_of(r["text"])) < 200
                                   and not re.search(r"(?i)<frame(set)?\b",
                                                     r["text"]))):
                        ok = False
                    emit(uid, name, cls,
                            "organization" if ok else "unverified_organization",
                            r.get("final_url") or u, st,
                            "TRIED: " + " | ".join(tried)
                            + " || website field published by the "
                            "organisation to DOI")
                    got_url = got_url or ok
                    if ok:
                        mr = probe_machine_readable(r["final_url"],
                                                    uid + "__mr")
                        if mr:
                            n_open += 1
                            emit(uid, name, cls,
                                    "machine_readable_surface",
                                    r["final_url"], 200,
                                    "TRIED: R5 machine-readable probe || "
                                    "open: " + ", ".join(mr))
                elif rec.get("website_none_listed"):
                    txt = (rec.get("website_field_text") or "").strip()
                    tried.append("R2 the organisation's own DOI entry states "
                                 "Website: "
                                 + (txt if txt else "None listed")
                                 + (" (not a host name; recorded as no "
                                    "website published)"
                                    if txt and not txt.lower()
                                    .startswith("none") else ""))
                # ---- R3 domain derived from a published email -----------
                for d in domains_from_emails(rec.get("emails") or [])[:2]:
                    if got_url:
                        break
                    u2, st2, verdict, note2 = try_host(
                        d, name, uid + "__mail_" + d, cls)
                    tried.append("R3 domain derived from published email @"
                                 + d + " -> " + verdict)
                    if verdict == "verified":
                        emit(uid, name, cls, "organization", u2, st2,
                                "TRIED: " + " | ".join(tried) + " || " + note2)
                        got_url = True
                    elif u2:
                        # THE DOMAIN IS STILL PUBLISHER-STATED EVEN WHEN IT
                        # SERVES NOTHING. alepahou.org is the Alepa Hou
                        # Foundation's domain -- it is in the email address
                        # the foundation filed with DOI -- and it returns an
                        # empty page. "Registered, nothing published" is a
                        # more useful and more accurate record than silence,
                        # and it tells the next agent not to re-derive it.
                        emit(uid, name, cls,
                             "parked_domain" if verdict == "parked_domain"
                             else "unverified_organization", u2, st2,
                             "TRIED: " + " | ".join(tried) + " || " + note2
                             + " || the DOMAIN is publisher-stated (it is in "
                               "the email address the organisation filed with "
                               "DOI); what it serves is not a site")
            else:
                tried.append("R2 DOI ONHR list: no entry matched this name "
                             "(register name may predate the April 2025 "
                             "revision)")

        # ---- R7 candidate domains derived from the name -----------------
        # Reached only when the publisher-stated routes gave nothing live.
        # Eleven tribes came out of the first pass without a verified site:
        # five where the BIA publishes a consortium profile instead of a
        # tribal domain, three where the BIA `website` field is empty, and
        # three where the site exists but refuses us. This rung is for the
        # first two groups.
        # NHOs ARE IN THIS RUNG TOO, AND THE REASON IS A CAUGHT FALSE NEGATIVE.
        # Pass 1 closed Makuʻu Farmers Association on the DOI list's
        # "Website: None listed". An independent check found makuu.org live and
        # makuufarmersassociation.org claimed. The DOI field is what the
        # organisation told its registrar, which is authoritative about the
        # organisation's STATEMENT and only as current as the last time it
        # updated the form. A publisher-stated negative is strong evidence; it
        # is not the end of the ladder, and treating it as one reproduced
        # exactly the false absence this workstream exists to prevent.
        # AND R7 IS OFF FOR INDIVIDUALLY NATIVE-OWNED BUSINESSES.
        # Even hardened, it matched "Laguna Creek LLC" to lagunacreek.org --
        # the Laguna Creek Watershed Council. Both name tokens on the page,
        # and the class markers available for a small business ("about us",
        # "contact us", "llc") are on essentially every website there is, so
        # the class test that saves the tribal and NHO cases does no work
        # here. A rung whose guard cannot discriminate for a class should not
        # run for that class. These entities are identified by UEI and CAGE in
        # SAM and SBA, which is where the next attempt should go; the honest
        # record for now is checked-and-not-found.
        if not got_url and cls in ("Federally recognized tribe",
                                   "Native Hawaiian Organization"):
            n_try = 0
            for h in candidate_hosts(row):
                if got_url or n_try >= 12:
                    break
                if restricted(h):
                    continue
                n_try += 1
                u2, st2, verdict, note2 = try_host(h, name,
                                                   uid + "__cand_" + h, cls)
                if verdict == "no_response":
                    continue
                tried.append("R7 candidate domain " + h + " -> " + verdict)
                if verdict == "verified":
                    emit(uid, name, cls,
                         {"Federally recognized tribe": "government",
                          "Native Hawaiian Organization": "organization"}
                         .get(cls, "corporate"), u2, st2,
                         "TRIED: " + " | ".join(tried) + " || " + note2
                         + " || DERIVED domain, name-verified against the "
                           "page; not published by the BIA directory.")
                    got_url = True
                    mr = probe_machine_readable(u2, uid + "__mr")
                    if mr:
                        n_open += 1
                        emit(uid, name, cls, "machine_readable_surface", u2,
                             200, "TRIED: R5 machine-readable probe || open: "
                             + ", ".join(mr))
            if n_try:
                tried.append("R7 tried " + str(n_try) + " derived candidate "
                             "domain(s) in total")
        elif cls == "Individually Native-owned business":
            tried.append("R7 domain derivation DELIBERATELY NOT RUN for this "
                         "class -- its guard cannot discriminate (see the "
                         "note at this rung); UEI/CAGE via SAM and SBA is the "
                         "route, and it is not attempted here")

        # ---- R4 IRS / ProPublica Nonprofit Explorer ---------------------
        # NOT FOR TRIBES. A federally recognized tribe is a government, not
        # an exempt organisation; it does not file a 990, so every hit is
        # some other body that shares its place name -- six of them did.
        # `o` IS RE-INITIALISED EVERY ENTITY, AND THAT IS NOT A STYLE POINT.
        # When the tribe branch was added, `if o:` ended up inside it, so no
        # NHO ever emitted a 990 row and four tribes emitted the LAST NHO's:
        # Fort Bidwell, Koi, Potter Valley and Samish were each given the
        # Royal Hawaiian Academy of Traditional Arts' EIN. A loop variable
        # that survives an iteration will eventually be read on an iteration
        # that never set it, and the value it carries looks exactly like a
        # real answer.
        o = None
        if not got_url and cls in ("Native Hawaiian Organization",
                                   "Individually Native-owned business"):
            o, note = propublica(name, (row.get("state") or "").strip())
            tried.append("R4 ProPublica Nonprofit Explorer -> " + note)
        elif not got_url and cls == "Federally recognized tribe":
            # NOT FOR TRIBES. A federally recognized tribe is a government,
            # not an exempt organisation; it does not file a 990, so every hit
            # is some other body sharing its place name -- six of them were.
            tried.append("R4 IRS/990 NOT RUN: a federally recognized tribe is "
                         "a government and does not file a 990; every match "
                         "this route produced for a tribe was a different "
                         "local organisation sharing the place name")
        if o:
            ein = o.get("strein") or str(o.get("ein"))
            emit(uid, name, cls, "form_990",
                 "https://projects.propublica.org/nonprofits/organizations/"
                 + str(o.get("ein")), 200,
                 "TRIED: " + " | ".join(tried) + " || IRS EIN " + ein
                 + " -- " + (o.get("name") or "") + ", "
                 + (o.get("city") or "") + " " + (o.get("state") or "")
                 + ". NOT a website: this is a filing record, and it is here "
                   "because it is a first row for an entity that had none.")

        # ---- R8 hand search ---------------------------------------------
        if not got_url and uid in R8_HAND_SEARCH:
            h8 = R8_HAND_SEARCH[uid]
            u8, st8, verdict, note8 = try_host(h8["host"], name,
                                               uid + "__r8", cls)
            tried.append("R8 hand search -> " + h8["host"] + " -> " + verdict)
            if verdict == "verified":
                emit(uid, name, cls,
                     "government" if cls == "Federally recognized tribe"
                     else "organization", u8, st8,
                     "TRIED: " + " | ".join(tried) + " || " + note8
                     + " || FOUND BY HAND SEARCH: " + h8["how"])
                got_url = True
                mr = probe_machine_readable(u8, uid + "__mr")
                if mr:
                    n_open += 1
                    emit(uid, name, cls, "machine_readable_surface", u8, 200,
                         "TRIED: R5 machine-readable probe || open: "
                         + ", ".join(mr))
            elif u8:
                emit(uid, name, cls,
                     "parked_domain" if verdict == "parked_domain"
                     else "unverified_government", u8, st8,
                     "TRIED: " + " | ".join(tried) + " || " + note8
                     + " || CANDIDATE FROM HAND SEARCH, NOT accepted as a "
                       "live site: " + h8["how"])

        # ---- R6 the honest negative -------------------------------------
        if not got_url:
            # THE NEGATIVE MUST NOT CONTRADICT THE ROWS BESIDE IT.
            # The first pass wrote `none_established` for Samish, Koi and
            # Scotts Valley -- each of which had just been written a row
            # naming a live site we were refused or challenged on. "None
            # found" beside "here is the URL" is not a mistake in wording, it
            # is two different answers in one ledger, and the coverage table
            # would have counted the wrong one. So the summary negative is
            # `none_established` ONLY when nothing at all was found, and
            # `no_own_site_found` when something was.
            if len(tried) < 3:
                tried.append("R5 machine-readable probe not reached -- no "
                             "host to probe")
            if len(tried) < 3:
                tried.append("R2/R3 not applicable to this entity class")
            ut = "none_established" if wrote[0] == 0 else "no_own_site_found"
            emit(uid, name, cls, ut, "", "",
                 "TRIED: " + " | ".join(tried) + " || CHECKED " + TODAY
                 + ", no verified site of the entity's own. This is an "
                   "attempted-and-none-found, NOT an untouched blank."
                 + ("" if wrote[0] == 0 else
                    " Other rows for this entity above record what WAS found."))
            n_none += 1
        else:
            n_url += 1
        if i % 10 == 0:
            print("    %d/%d  %d with a URL, %d none found"
                  % (i, len(todo), n_url, n_none))
    print("  shard_n done: %d entities with a URL, %d checked-none-found, "
          "%d hosts with an open machine-readable surface"
          % (n_url, n_none, n_open))
    write_doc()
    return 0


# -------------------------------------------------------------------- doc
OUT_DOC = os.path.join(ROOT, "docs", "COVERAGE_TAIL_SHARD_N.md")

# What each url_type means for the question "does this entity have a website".
# Kept here rather than inferred, because the whole point of the shard is that
# these outcomes are DIFFERENT and a reader must not have to guess which ones
# the coverage number counted.
LIVE_TYPES = {"government", "organization", "corporate"}
EXISTS_BUT_REFUSED = {"government_refused_robots",
                      "government_blocked_bot_protection",
                      "TERMS_RESTRICTED_DO_NOT_HARVEST"}
NOT_THE_ENTITYS_SITE = {"directory_profile", "form_990"}


def write_doc():
    from collections import Counter, defaultdict
    reg = {r["cedar_uid"]: r for r in read_register() if r.get("cedar_uid")}
    if not os.path.exists(WEBMAP):
        return
    with open(WEBMAP, encoding="utf-8-sig", errors="replace",
              newline="") as fh:
        rows = list(csv.DictReader(fh))
    by = defaultdict(list)
    for r in rows:
        by[r["cedar_uid"]].append(r)

    def state(rs):
        t = {x["url_type"] for x in rs}
        if t & LIVE_TYPES:
            return "has a site of its own"
        if t & EXISTS_BUT_REFUSED:
            return "site exists, we are refused or challenged"
        if t & NOT_THE_ENTITYS_SITE:
            return "no site of its own; another party publishes about it"
        return "checked, no web presence located"

    st = {u: state(rs) for u, rs in by.items()}
    cls = {u: (reg.get(u, {}).get("entity_class") or by[u][0]["entity_class"])
           for u in by}
    grid = defaultdict(Counter)
    for u, s in st.items():
        grid[cls[u]][s] += 1
    order = ["has a site of its own",
             "site exists, we are refused or challenged",
             "no site of its own; another party publishes about it",
             "checked, no web presence located"]

    L = ["# The coverage tail — shard N", "",
         "*Generated " + TODAY + " by `code/1020_tail_web_probe.py`. Map: "
         "`data/staging/tribe_web_map/shard_n.csv`. STAGING — promoting any "
         "URL here to `entity_website` is an assertion and goes through 510.*",
         "",
         "Shard N's slice is derived, not listed: every register entity that "
         "no other shard map has a row for. That set was **" + str(len(by))
         + "** when this ran, and it is exactly the `untouched` column of "
           "`docs/SHARD_COVERAGE.md` — the column that says nobody tried.",
         "",
         "## Four outcomes, and none of them is the others", "",
         "| entity class | " + " | ".join(order) + " |",
         "|---" * (len(order) + 1) + "|"]
    tot = Counter()
    for c in sorted(grid, key=lambda k: -sum(grid[k].values())):
        L.append("| " + c + " | "
                 + " | ".join(str(grid[c].get(o, 0)) for o in order) + " |")
        tot.update(grid[c])
    L.append("| **total** | " + " | ".join("**" + str(tot.get(o, 0)) + "**"
                                           for o in order) + " |")
    # DERIVE THE NUMBER, DO NOT WRITE IT IN THE PROSE. A hand-typed "64 of
    # 69" in a generated document is a claim that stops being true on the next
    # run and never says so.
    n_doi_none = sum(1 for u, rs in by.items()
                     if cls[u] == "Native Hawaiian Organization"
                     and any("Website: None listed" in x["evidence"]
                             for x in rs))
    n_nho = sum(1 for u in by if cls[u] == "Native Hawaiian Organization")
    L += ["", "*`checked, no web presence located` is a FINDING. Every one of "
              "those entities carries a row naming the routes run and the "
              "date. For **" + str(n_doi_none) + " of the " + str(n_nho)
              + "** Native Hawaiian Organizations here, the route that "
                "settled it was the organisation's own entry in the DOI "
                "Office of Native Hawaiian Relations notification list, which "
                "records `Website: None listed`. That is the organisation "
                "telling its registrar it has none — not us failing to find "
                "one.*", "",
          "## Rows by type", "", "| url_type | n | meaning |", "|---|---:|---|"]
    mean = {
        "government": "verified tribal government site",
        "organization": "verified organisation site",
        "corporate": "verified company site",
        "machine_readable_surface": "the host answers wp-json / sitemap / "
                                    "feed — a harvestable surface for the "
                                    "next agent",
        "form_990": "IRS filing record ABOUT the entity; not its website",
        "directory_profile": "a consortium or directory page about the "
                             "entity, published in the BIA `website` field",
        "government_refused_robots": "site exists; robots.txt Disallow: / — "
                                     "refused by every route",
        "government_blocked_bot_protection": "site exists; 403 to research UA "
                                             "AND to browser headers",
        "unverified_government": "URL published by the BIA that did not answer",
        "unverified_organization": "URL published by DOI that did not answer",
        "none_established": "checked, nothing found at all",
        "no_own_site_found": "checked; something was found but not a site of "
                             "the entity's own",
        "TERMS_RESTRICTED_DO_NOT_HARVEST": "site exists; the publisher's stated "
                                       "terms or a robots rule naming this "
                                       "agent refuse us. Not fetched by any "
                                       "route",
    }
    for k, v in Counter(r["url_type"] for r in rows).most_common():
        L.append("| `%s` | %d | %s |" % (k, v, mean.get(k, "")))

    hard = sorted((cls[u], reg.get(u, {}).get("canonical_name")
                   or by[u][0]["canonical_name"], u)
                  for u, s in st.items()
                  if s in ("site exists, we are refused or challenged",
                           "no site of its own; another party publishes "
                           "about it"))
    if hard:
        L += ["", "## Reached but not harvestable — " + str(len(hard)), "",
              "*These are not coverage gaps and they are not absences. Filing "
              "either one as `none found` would misreport a nation's own "
              "decision, or an edge WAF, as an empty web presence.*", "",
              "| entity | class | outcome | what was seen |",
              "|---|---|---|---|"]
        for c, n, u in hard:
            rs = by[u]
            pick = next((x for x in rs if x["url_type"] in EXISTS_BUT_REFUSED
                         or x["url_type"] in NOT_THE_ENTITYS_SITE), rs[0])
            L.append("| %s | %s | %s | `%s` %s |"
                     % (n, c, st[u], pick["url_type"], pick["url"][:70]))
    with open(OUT_DOC, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("  wrote " + OUT_DOC)
    write_candidates(rows, reg)


# THE CONSTELLATION AGENT OWNS `serves`. THIS FILE ONLY REPORTS.
# A `directory_profile` is evidence of a real relationship -- the BIA's
# `website` field for five California rancherias points at the California
# Tribal Families Coalition or the Southern California Tribal Chairmen's
# Association, which is those bodies serving those tribes. That is a `serves`
# edge and it is not this shard's to write, so the candidates go to review
# with the evidence and the constellation agent decides.
SERVES_HOSTS = {
    "caltribalfamilies.org": "California Tribal Families Coalition",
    "sctca.net": "Southern California Tribal Chairmen's Association",
}
CAND = os.path.join(ROOT, "review",
                    "1020_constellation_serves_candidates.csv")


def write_candidates(rows, reg):
    out = []
    for r in rows:
        if r["url_type"] != "directory_profile":
            continue
        host = urllib.parse.urlsplit(r["url"]).netloc.lower()
        host = host[4:] if host.startswith("www.") else host
        if host not in SERVES_HOSTS:
            continue
        out.append({
            "served_cedar_uid": r["cedar_uid"],
            "served_canonical_name": r["canonical_name"],
            "served_entity_class": r["entity_class"],
            "serving_organisation_name": SERVES_HOSTS[host],
            "serving_organisation_host": host,
            "evidence_url": r["url"],
            "evidence": "the BIA Tribal Leaders Directory publishes THIS url "
                        "in its `website` field for this tribe, i.e. the "
                        "federal directory treats the consortium page as the "
                        "tribe's public presence",
            "proposed_edge": "serves",
            "identity_resolved": "NO - the serving organisation is named, not "
                                 "resolved to a cedar_uid; shard N does not "
                                 "resolve identity",
            "found_by": "code/1020_tail_web_probe.py (shard_n)",
            "checked_date": TODAY,
        })
    if not out:
        return
    os.makedirs(os.path.dirname(CAND), exist_ok=True)
    with open(CAND, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        for x in out:
            w.writerow(x)
    print("  wrote %d serves candidate(s) for the constellation agent -> %s"
          % (len(out), CAND))


# ----------------------------------------------------------------- verify
def check(path=WEBMAP):
    """The invariants. Returns a list of violations; empty means clean.

    (1) every cedar_uid is in the register  -- a shard may not invent identity
    (2) no TERMS_STATED_RESTRICTIVE host or entity appears with a URL
    (3) every `none_established` row names >= 3 routes tried -- the rule from
        HIDDEN_DATA_TECHNIQUES that a negative from search alone is not a
        negative, enforced rather than intended
    (4) no duplicate (uid, url_type, url)
    (5) every row carries checked_date -- 'when' is half of the record
    (6) a DERIVED domain typed as a live site must record that the page
        carried ALL of the entity's tokens. Added after R7 wrote ten
        fabricated sites on circular evidence; see `name_evidence`.
    (7) a live site whose recorded body is under 700 bytes is refused. Two
        tribal sites were accepted on a 169-byte captcha interstitial that
        returned HTTP 200.
    (8) no host that any row records as REFUSED may appear with a 2xx on any
        other row. A redirect from an unrestricted domain onto a robots-
        disallowed one produced exactly that for the Samish Indian Nation.
    (9) a `form_990` row's filer name must carry every distinctive token of
        the entity's name. Caught four tribes sharing one Hawaiian arts
        academy's EIN, from a loop variable that outlived its iteration.
    (10) an entity whose name is only generic words may hold a live URL only
        from a publisher-stated route. Nothing on a page can identify it --
        the village of *Council* matched `kawerak.org` in a sibling sweep.
    (11) no 2xx from a host on the terms/named-agent refusal list.
    """
    bad = []
    if not os.path.exists(path):
        return ["shard_n.csv has never been written"]
    known = {r["cedar_uid"] for r in read_register() if r.get("cedar_uid")}
    seen = set()
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows_all = list(csv.DictReader(fh))
    # (8) A HOST THAT REFUSED US MAY NOT APPEAR WITH A 2xx ANYWHERE.
    # samishindiannation.org 301s to www.samishtribe.nsn.us, whose robots.txt
    # disallows everything. The robots check ran on the host asked for, the
    # bytes came from the host that had said no, and the map ended up holding
    # BOTH a `government_refused_robots` row for that host and a 200 for it.
    # A refusal that another row contradicts is not a refusal that was
    # honoured. Cross-row, because no single row can see this.
    refused_hosts = set()
    for r in rows_all:
        if "REFUSED" in str(r.get("http_status") or ""):
            h = urllib.parse.urlsplit(r.get("url") or "").netloc.lower()
            if h:
                refused_hosts.add(h[4:] if h.startswith("www.") else h)
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for i, r in enumerate(csv.DictReader(fh), 2):
            _h = urllib.parse.urlsplit(r.get("url") or "").netloc.lower()
            _h = _h[4:] if _h.startswith("www.") else _h
            if _h and _h in refused_hosts \
                    and str(r.get("http_status") or "").startswith("2"):
                bad.append("line %d: %s carries a 2xx from %s, a host another "
                           "row records as REFUSED -- a redirect landed on a "
                           "host that had said no"
                           % (i, r.get("cedar_uid"), _h))
            uid = (r.get("cedar_uid") or "").strip()
            ut = (r.get("url_type") or "").strip()
            url = (r.get("url") or "").strip()
            ev = r.get("evidence") or ""
            if uid not in known:
                bad.append("line %d: cedar_uid %r is not in the register"
                           % (i, uid))
            # RECORDING A REFUSAL IS NOT HARVESTING ONE.
            # The first form of this rule rejected the row that SAYS a host
            # refused us, which would force the refusal to be silent -- and a
            # silent refusal is indistinguishable from an entity nobody tried,
            # which is the conflation this whole shard exists to prevent. What
            # must not exist is CONTENT from that host; invariant (11) covers
            # the 2xx case, and this one covers everything except an explicit
            # refusal row.
            if url and restricted(url)                     and ut not in ("TERMS_RESTRICTED_DO_NOT_HARVEST",
                                   "government_refused_robots"):
                bad.append("line %d: %s is TERMS_STATED_RESTRICTIVE and may "
                           "appear only on an explicit refusal row, not as "
                           "`%s`" % (i, url, ut))
            if ut in ("none_established", "no_own_site_found"):
                n = len([x for x in ev.split(" | ") if x.strip()])
                if "TRIED:" not in ev or n < 3:
                    bad.append("line %d: %s recorded as %s with "
                               "only %d route(s) named -- a negative from "
                               "search alone is not a negative"
                               % (i, uid, ut, n))
            # (6) A DERIVED DOMAIN MAY NOT BE TYPED AS A LIVE SITE UNLESS THE
            # PAGE CARRIED THE WHOLE NAME. This is the invariant the ten
            # fabricated rows would have tripped. R1 and R2 rows are exempt:
            # a URL the BIA or DOI publishes for an entity is publisher-stated
            # and needs no page-text proof.
            if ut in ("government", "organization", "corporate") \
                    and "DERIVED domain" in ev \
                    and "tokens ALL present" not in ev:
                bad.append("line %d: %s is typed `%s` from a DERIVED domain "
                           "without full name evidence on the page -- this is "
                           "the circular-evidence defect of 2026-09-02"
                           % (i, uid, ut))

            # (7) A LIVE SITE WITH A BODY TOO SMALL TO BE ONE.
            # Potter Valley and the Paiute Indian Tribe of Utah were recorded
            # as `government` on a 200 carrying 169 bytes of SiteGround
            # captcha. The byte count is now written into the evidence, so the
            # gate can read it back and refuse the claim.
            mb = re.search(r"verified 2xx, (\d+) bytes", ev)
            if ut in ("government", "organization", "corporate") and mb \
                    and int(mb.group(1)) < 700:
                bad.append("line %d: %s typed `%s` on a %s-byte body -- too "
                           "small to be a website; check for a bot challenge "
                           "or a placeholder"
                           % (i, uid, ut, mb.group(1)))

            # (9) A 990 ROW MUST NAME A FILER THAT CARRIES THE ENTITY'S NAME.
            # Four tribes were written the same EIN, belonging to a Hawaiian
            # arts academy, because a loop variable outlived its iteration.
            # Nothing in the row itself looked wrong; only the relationship
            # between the entity name and the filer name did.
            if ut == "form_990":
                mfl = re.search(r"IRS EIN [\d-]+ -- ([^,]+),", ev)
                if mfl:
                    want = set(tokens(_deaccent(r.get("canonical_name", ""))))
                    got = set(tokens(_deaccent(mfl.group(1))))
                    if want and not want.issubset(got):
                        bad.append("line %d: %s is given the 990 of %r, which "
                                   "does not carry its name (%s)"
                                   % (i, uid, mfl.group(1)[:44],
                                      ",".join(sorted(want - got))[:40]))

            # (10) AN ENTITY WITH NO DISTINCTIVE TOKENS MAY NOT HOLD A
            # PAGE-TEXT-VERIFIED URL. Nothing on a page can identify it, so
            # any live URL it holds must be publisher-stated (R1 BIA, R2 DOI,
            # R3 a domain from its own published email) and must say so.
            if ut in ("government", "organization", "corporate")                     and not tokens(_deaccent(r.get("canonical_name", ""))):
                if not any(t in ev for t in ("R1 BIA", "R2 DOI",
                                             "R3 domain derived")):
                    bad.append("line %d: %s has a name of only generic words "
                               "and a live URL that is not publisher-stated "
                               "-- no page-text check can identify it"
                               % (i, uid))

            # (11) A HOST WHOSE robots.txt NAMES THIS AGENT MAY NOT APPEAR
            # WITH A 2xx. Held as a list here rather than re-fetched, so the
            # gate is offline and deterministic.
            if str(r.get("http_status") or "").startswith("2")                     and url and restricted(url):
                bad.append("line %d: %s carries a 2xx from %s, a host whose "
                           "publisher has refused this agent"
                           % (i, uid, url[:60]))

            k = (uid, ut, url)
            if url and k in seen:
                bad.append("line %d: duplicate row %s" % (i, str(k)))
            seen.add(k)
            if not (r.get("checked_date") or "").strip():
                bad.append("line %d: no checked_date" % i)
    return bad


def selftest():
    """Prove the gate fires. Writes a synthetic violation to a temp file and
    asserts check() rejects it -- a verify that has never failed is a verify
    nobody has tested."""
    import tempfile
    p = os.path.join(tempfile.gettempdir(), "shard_n_selftest.csv")
    cases = [
        ("unknown uid",
         ["CE-NOTREAL-00", "x", "y", "government", "https://a.example", "200",
          TODAY, "TRIED: a | b | c"]),
        ("thin negative",
         [None, "x", "y", "none_established", "", "", TODAY,
          "TRIED: searched the name"]),
        ("restricted host",
         [None, "x", "y", "government", "https://colvilletribes.com/", "200",
          TODAY, "TRIED: a | b | c"]),
        ("2xx from a host that refused us", None),
        ("generic name, guessed URL",
         [None, "Council", "y", "government", "https://kawerak.org", "200",
          TODAY, "TRIED: a | b | c || DERIVED domain, name-verified against "
                 "the page; tokens ALL present"]),
        ("2xx from a refused host",
         [None, "x", "y", "government", "https://penobscotnation.org/", "200",
          TODAY, "TRIED: a | b | c"]),
        ("990 filer with the wrong name",
         [None, "Potter Valley", "y", "form_990",
          "https://projects.propublica.org/nonprofits/organizations/1", "200",
          TODAY, "TRIED: a | b | c || IRS EIN 99-0339530 -- Royal Hawaiian "
                 "Academy Of Traditional Arts, Honolulu HI."]),
        ("live site, 169-byte body",
         [None, "x", "y", "government", "https://a.example", "200", TODAY,
          "TRIED: a | b | c || verified 2xx, 169 bytes of body"]),
        ("derived, no name proof",
         [None, "x", "y", "government", "https://fort.org", "200", TODAY,
          "TRIED: a | b | c || DERIVED domain, name-verified against the "
          "page; not published by the BIA directory."]),
        ("missing checked_date",
         [None, "Penobscot Nation", "y", "government", "https://a.example",
          "200", "",
          "TRIED: a | b | c"]),
    ]
    real = next(r["cedar_uid"] for r in read_register() if r.get("cedar_uid"))
    fails = 0
    for label, row in cases:
        if row is None:                       # two-row fixture
            with open(p, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                w.writerow(WEBMAP_COLS)
                w.writerow([real, "x", "y", "government_refused_robots",
                            "https://www.example-refused.org/",
                            "REFUSED_ROBOTS_DISALLOW", TODAY,
                            "TRIED: a | b | c"])
                w.writerow([real, "x", "y", "government",
                            "https://www.example-refused.org/", "200", TODAY,
                            "TRIED: a | b | c"])
            v = check(p)
            print("    selftest %-22s -> %s"
                  % (label, v[0] if v else "NOT CAUGHT"))
            if not v:
                fails += 1
            continue
        row = list(row)
        if row[0] is None:
            row[0] = real
        with open(p, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(WEBMAP_COLS)
            w.writerow(row)
        v = check(p)
        print("    selftest %-22s -> %s" % (label, v[0] if v else "NOT CAUGHT"))
        if not v:
            fails += 1
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(WEBMAP_COLS)
        w.writerow([real, "x", "y", "none_established", "", "", TODAY,
                    "TRIED: R1 bia | R2 doi | R4 propublica"])
    v = check(p)
    print("    selftest %-22s -> %s"
          % ("clean row", v[0] if v else "accepted (correct)"))
    if v:
        fails += 1
    os.remove(p)
    return 1 if fails else 0


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "selftest":
        return selftest()
    if arg == "doc":
        write_doc()
        return 0
    if arg == "verify":
        bad = check()
        for b in bad[:40]:
            print("    VIOLATION  " + b)
        print("  1020 shard_n verify: %d violation(s)" % len(bad))
        return 1 if bad else 0
    return run()


if __name__ == "__main__":
    sys.exit(main())
