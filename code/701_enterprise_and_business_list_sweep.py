"""701_enterprise_and_business_list_sweep.py — WORKSTREAM ENTERPRISE, read-only.

WHY THIS EXISTS
---------------
Shards L and M swept 297 unsurveyed federally recognized tribes and both
independently returned a ~3.4% hit rate. They searched TERO VOCABULARY. The
owner named the flaw:

    "A tribe may not have TERO, or obviously has TERO but maintains
     member-owned lists."

The absence of a TERO office is not the absence of a business list. Shard L
tripped over the evidence by accident — its broader count was 11 of 149 (7.4%),
and the six extra finds came through WordPress custom post types literally
named `enterprise` and `tribalbusiness`, not through any TERO term.

This script re-probes with business-list vocabulary that has NOTHING to do with
TERO, and separately harvests TRIBAL ENTERPRISE REGISTERS — a nation listing
its own subsidiaries, which is parent-asserted ownership and the strongest
evidence class in the project (docs/IDENTIFIER_STANDARD.md, hub / sub-hub).

SELECTION DECLARATION
---------------------
Leg used      KNOWN_IDENTIFIER only — the 359 rows of
              review/tribal_vendor_list_registry_2026-08-26.csv, which is the
              spine's federally-recognized tribe roster plus the 62-tribe
              original survey. There is no TYPE_FILTER for "tribe that
              publishes a business list": no registry of such lists exists to
              filter on, so the identifier leg here IS the population, not a
              sample of one.
Leg missing   none available.
population_basis   `spine_federally_recognized_tribe` on every row emitted.

STAGES
------
--offline   ZERO network. Re-reads files this project already owns
            (PULL_DISCIPLINE tier 1): shard M's media_inventory.csv (31,393
            rows), every recorded custom-post-type list from shards L and M,
            and shard L's saved raw bodies — rescanned with the new
            vocabulary. Four of seven findings in PRE2007_SPENDING_SOURCES
            came from re-reading owned files; this is the same move.
--online    Per host, IN THIS ORDER, and the order is the point:
              1. robots.txt   fetched with OUR declared UA and handed to
                              RobotFileParser.parse().  .read() fetches with
                              `Python-urllib` and reads a 403 on the robots
                              file as disallow_all — 22 hosts were lost to
                              that in one shard today.
              2. homepage     the served page must NAME THE ENTITY. Six
                              hijacked or lapsed tribal domains were found on
                              2026-09-01 serving a Thai casino, Indonesian
                              slots, adult video, an electronics blog, a link
                              farm and a porn redirect. A domain that answers
                              is not the right domain.
              3. terms        BEFORE any enumeration, never after.
              4. wp/v2/types  custom post types — the highest-yield signal,
                              and the route that produced both prior finds.
              5. wp/v2/search the TERO-free term list.
              6. wp/v2/media  per_page=100, paginated, UNFILTERED BY MIME.
                              Shard M's best find was a .docx; a PDF-only
                              filter would have missed it.
              7. sitemap      sitemap_index / sitemap / wp-sitemap.

EXCLUSIONS — ONE PLACE IN CODE
------------------------------
`excluded_hosts()` is the ONLY definition of what is off limits, and every
route calls `is_excluded()`. Shard M's --deep mode re-probed a restricted host
because its check read a hard-coded constant instead of the verdict the same
script had written. The set is built from the registry's own
`source_terms_status` / `consent_status` verdicts UNIONED with the named list
in docs/PUBLICATION_POLICY.md, so a verdict written by any pass binds this one.

WHAT IT WRITES
--------------
data/staging/tribal_enterprises/    enterprise_register.jsonl  (job 1)
                                    business_list_candidates.jsonl
                                    host_log.jsonl
                                    _state.json
review/tribal_vendor_list_registry_2026-08-26.csv   appends to the
    `hidden_route_sweep_2026-09-01` / verdict columns only (never a new row).

It MINTS NOTHING, writes nothing to data/clean or the spine, and RESOLVES NO
IDENTITY. Candidate entity matches carry a confidence and stay candidates.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
import threading
import time
import urllib.parse as up
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
IDREG = ROOT / "data" / "spine" / "cedar_identity_register.csv"
HARVEST = ROOT / "data" / "staging" / "tribe_harvest"
OUT = ROOT / "data" / "staging" / "tribal_enterprises"
OUT.mkdir(parents=True, exist_ok=True)

ENTERPRISE_JSONL = OUT / "enterprise_register.jsonl"
CAND_JSONL = OUT / "business_list_candidates.jsonl"
HOSTLOG = OUT / "host_log.jsonl"
STATE = OUT / "_state.json"
RAW = OUT / "raw"

TODAY = "2026-09-01"
UA = ("CedarPress-research/1.0 (tribal business-register survey; "
      "contact elijahsamsonmoreno@gmail.com)")
HEADERS = {"User-Agent": UA, "Accept": "*/*"}
BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36 CedarPress-research/1.0 "
                   "(contact elijahsamsonmoreno@gmail.com)"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
}

PER_HOST_DELAY = 1.2
WORKERS = 6
TIMEOUT = 22
MEDIA_PAGE_CAP = 25
RUN_DEADLINE_H = 2.0
_deadline = [0.0]

# ---------------------------------------------------------------------------
# THE VOCABULARY. Deliberately contains NO TERO term, no "indian preference",
# no "tribal employment rights". That is the whole experiment: shards L and M
# searched those and returned 3.4%.
# ---------------------------------------------------------------------------

# Tier 1 — a nation listing its own companies. Parent-asserted ownership.
ENTERPRISE_PAT = re.compile(
    r"\benterprise[sz]?\b|tribal[\s\-_]*business|tribalbusiness|"
    r"\bsubsidiar|\bholding[s]?\b|our[\s\-_]*compan|"
    r"portfolio[\s\-_]*(of[\s\-_]*)?(compan|business|enterprise)|"
    r"(compan|business|enterprise)[a-z]*[\s\-_]*(we|the[\s\-_]*(tribe|nation))"
    r"[\s\-_]*own|"
    r"business[\s\-_]*(entit|arm|division)|corporate[\s\-_]*(famil|structure)|"
    r"economic[\s\-_]*development[\s\-_]*(corp|author|entit)",
    re.I)

# Tier 2 — a list of businesses owned by members/citizens, or licensed by the
# nation. Not TERO, not "indian preference".
MEMBERLIST_PAT = re.compile(
    r"member[\s\-_]*owned|citizen[\s\-_]*owned|tribal(ly)?[\s\-_]*owned|"
    r"native[\s\-_]*owned|business[\s\-_]*director|director\w*[\s\-_]*of"
    r"[\s\-_]*business|business[\s\-_]*(regist|listing|roster|guide|index)|"
    r"chamber[\s\-_]*of[\s\-_]*commerce|"
    r"(tribal|business|native|indian)[\s\-_]*chamber|"
    r"entrepreneur|small[\s\-_]*business[\s\-_]*(list|direct|regist)|"
    r"artisan|\bcraftspeople\b|"
    r"(approved|active|current|licen[cs]ed)[\s\-_]*business[\s\-_]*"
    r"(licen[cs]e|list)|business[\s\-_]*licen[cs]e[sd]?[\s\-_]*"
    r"(list|regist|roster|report|issued)|"
    r"certified[\s\-_]*\w*[\s\-_]*business[\s\-_]*list",
    re.I)

# Things that look like the vocabulary but are a FORM, a job ad or a code —
# not a list. Kept separate so a negative stays honest and visible.
NOTALIST_PAT = re.compile(
    r"applicat|\bform\b|agreement|acknowledg|\bpacket\b|"
    r"job[\s\-_]*descript|position|\bhiring\b|\bresume\b|"
    r"withhold|w-?9\b|invoice|\bach\b|direct[\s\-_]*deposit|"
    r"powwow|pow[\s\-_]*wow|bazaar|festival|booth|"
    r"ordinance|\bcode\b|\btitle[\s\-_]*\d|chapter[\s\-_]*\d|bylaw|"
    r"resolution[\s\-_]*\d|\brfp\b|request[\s\-_]*for[\s\-_]*proposal|"
    r"press[\s\-_]*release|newsletter|minutes",
    re.I)

# REST search terms. Six, all TERO-free.
SEARCH_TERMS = ["enterprise", "subsidiaries", "chamber",
                "economic development", "business directory", "entrepreneur"]

# Paths a business/enterprise page lives at, for the sitemap match.
PATH_PAT = re.compile(
    r"/(enterprise[sz]?|tribal-?business(es)?|business-?director|"
    r"member-?owned|citizen-?owned|tribally-?owned|our-?compan|"
    r"subsidiar|holdings?|economic-?development|chamber|commerce|"
    r"entrepreneur|small-?business|artisan)", re.I)

TERMS_FORBID_PAT = re.compile(
    r"may not (be )?(copy|reproduce|redistribut|extract|download|scrap)|"
    r"(no|not|prohibit\w*|forbid\w*)[^.]{0,80}"
    r"(scrap|crawl|spider|robot|automated (means|access|tool)|data ?min)|"
    r"(scrap|crawl|spider|harvest)\w*[^.]{0,60}(prohibit|forbid|not permitted|"
    r"without (our |the )?(prior |express )*written (permission|consent))|"
    r"unauthori[sz]ed (use|reproduction|copying|extraction)",
    re.I)

# A TRADEMARK notice is not a data-reuse restriction, and conflating the two
# would refuse a nation that never refused us. The registry already carries
# `TERMS_STATED_COPYRIGHT_ONLY` as a distinct, non-excluding verdict on four
# rows written by earlier passes; this reproduces that distinction. Measured
# on choctawnation.com/copyright-and-trademarks/, whose only trigger was
# "Unauthorized use ... may be trademark infringement" about its LOGO.
# A publisher that means content says so in content words: copy, reproduce,
# redistribute, extract, scrape, data mining. Those still bind.
MARK_CONTEXT_PAT = re.compile(
    r"trademark|service ?mark|\blogo|\bmarks?\b|trade dress|infringement",
    re.I)
TERMS_PATHS = ["/terms-of-use", "/terms", "/terms-and-conditions", "/legal"]

CPT_SKIP = {
    "post", "page", "attachment", "nav_menu_item", "wp_block", "wp_template",
    "wp_template_part", "wp_navigation", "wp_font_family", "wp_font_face",
    "wp_global_styles", "revision", "menu-item", "custom_css",
    "customize_changeset", "oembed_cache", "user_request", "amp_validated_url",
}

# Hijack signature. A domain that answers is not the right domain.
# WORD-BOUNDED, every token. An unbounded `judi` matched "Judicial Branch" and
# flagged cherokee.org, cskt.org and gilariver.org as hijacked in the smoke
# test — a false hijack silently deletes a real tribe from the sweep, which is
# the same class of error as the robots false-block in PULL_DISCIPLINE.md.
HIJACK_PAT = re.compile(
    r"\bslot ?gacor\b|\bsitus (judi|slot|togel)\b|\bjudi bola\b|\btogel\b|"
    r"\bbandar (judi|togel|bola)\b|\bcasino online\b|\bagen slot\b|"
    r"\bpornhub\b|\bxvideos\b|\bxnxx\b|\bescort service\b|"
    r"buy (viagra|cialis)|\bcbd gummies\b|"
    r"this domain (is|may be) for sale|hugedomains|godaddy auction|"
    r"domain is parked|parked free|sedo\.com|\bdan\.com\b",
    re.I)


# ---------------------------------------------------------------------------
# EXCLUSIONS — the ONE definition. Everything calls is_excluded().
# ---------------------------------------------------------------------------

_EXCLUDED: set[str] | None = None
_EXCL_REASON: dict[str, str] = {}

# The named list from docs/PUBLICATION_POLICY.md. Present so that a registry
# row losing its verdict cannot silently re-open a refused publisher. It is
# UNIONED into the registry verdicts, never consulted on its own.
NAMED_RESTRICTIVE = {
    "colvilletribes.com": "PUBLICATION_POLICY: Confederated Colville",
    "ctuir.org": "PUBLICATION_POLICY: CTUIR / Umatilla",
    "yakama.com": "PUBLICATION_POLICY: Yakama",
    "yakamanation-nsn.gov": "PUBLICATION_POLICY: Yakama",
    "chickasaw.net": "PUBLICATION_POLICY: Chickasaw (names directories)",
    "chickasawbusinessnetwork.com": "PUBLICATION_POLICY: Chickasaw",
    "nana.com": "PUBLICATION_POLICY: NANA (forbids automated use)",
    "akima.com": "PUBLICATION_POLICY: Akima / NANA",
    "southernute-nsn.gov": "PUBLICATION_POLICY: Southern Ute",
    "sugf.com": "PUBLICATION_POLICY: Southern Ute Growth Fund",
    "fcpotawatomi.com": "PUBLICATION_POLICY: Forest County Potawatomi",
    "fcpotawatomi-nsn.gov": "PUBLICATION_POLICY: Forest County Potawatomi",
    "stillaguamish.com": "PUBLICATION_POLICY: Stillaguamish",
}


def _bare(host: str) -> str:
    h = (host or "").strip().lower()
    h = h.split("//")[-1].split("/")[0].split(":")[0]
    return h[4:] if h.startswith("www.") else h


def excluded_hosts() -> dict[str, str]:
    """The single source of truth. host (bare, no www) -> reason.

    Built from the registry's OWN verdicts, unioned with the named policy list.
    A verdict written by any earlier pass binds this one; that is the point.
    """
    global _EXCLUDED
    if _EXCLUDED is not None:
        return _EXCL_REASON
    _EXCL_REASON.clear()
    for h, why in NAMED_RESTRICTIVE.items():
        _EXCL_REASON[_bare(h)] = why
    with open(REGISTRY, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            bad = (r.get("source_terms_status") == "TERMS_STATED_RESTRICTIVE"
                   or r.get("consent_status") == "OPT_OUT"
                   or r.get("source_terms_status") == "ROBOTS_DISALLOW")
            if not bad:
                continue
            why = (f"registry verdict {r.get('source_terms_status')} for "
                   f"{r.get('canonical_name')}")
            for h in ([r.get("official_site", "")]
                      + (r.get("hosts", "") or "").split(";")):
                b = _bare(h)
                if b:
                    _EXCL_REASON.setdefault(b, why)
    _EXCLUDED = set(_EXCL_REASON)
    return _EXCL_REASON


def is_excluded(host: str) -> str | None:
    """Return the reason this host is off limits, or None. THE ONLY CHECK."""
    reasons = excluded_hosts()
    b = _bare(host)
    if b in reasons:
        return reasons[b]
    # a subdomain of a refused apex is refused too
    for bad, why in reasons.items():
        if b.endswith("." + bad):
            return why
    return None


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

_host_lock: dict[str, threading.Lock] = {}
_host_last: dict[str, float] = {}
_glock = threading.Lock()
_nreq = [0]


def _pace(host: str):
    with _glock:
        lk = _host_lock.setdefault(host, threading.Lock())
    with lk:
        last = _host_last.get(host, 0.0)
        wait = PER_HOST_DELAY - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        _host_last[host] = time.time()


def fetch(url: str, headers=None, verify=True, timeout=TIMEOUT):
    """One GET. Returns dict; never raises. Refuses an excluded host outright."""
    host = _bare(up.urlparse(url).netloc)
    why = is_excluded(host)
    if why:
        return {"ok": False, "status": "EXCLUDED", "text": "", "headers": {},
                "url": url, "excluded_reason": why}
    if time.time() > _deadline[0]:
        return {"ok": False, "status": "RUN_DEADLINE", "text": "",
                "headers": {}, "url": url}
    _pace(host)
    try:
        r = requests.get(url, headers=headers or HEADERS, timeout=timeout,
                         verify=verify, allow_redirects=True)
        with _glock:
            _nreq[0] += 1
        return {"ok": True, "status": r.status_code, "text": r.text,
                "headers": {k.lower(): v for k, v in r.headers.items()},
                "url": r.url}
    except requests.RequestException as exc:
        with _glock:
            _nreq[0] += 1
        return {"ok": False, "status": type(exc).__name__, "text": "",
                "headers": {}, "url": url}


def robots_ok(root: str, path: str = "/") -> tuple[bool, str]:
    """Fetch robots.txt with OUR UA and .parse() the body.

    RobotFileParser.read() fetches with the default `Python-urllib` UA; hosts
    that block that UA return 403 for the robots file and the parser reads a
    403 as disallow_all. Twenty-two hosts were lost to that in one shard today.
    A 404 or an empty file means ALLOWED.
    """
    r = fetch(root.rstrip("/") + "/robots.txt")
    if r["status"] == "EXCLUDED":
        return False, "excluded"
    body = r["text"] if (r["ok"] and r["status"] == 200) else ""
    if r["ok"] and r["status"] == 200 and "<html" in body[:400].lower():
        body = ""          # a soft-404 HTML page is not a robots file
    rp = RobotFileParser()
    rp.parse(body.splitlines() if body else [])
    allowed = rp.can_fetch(UA, root.rstrip("/") + path)
    dis = [l.strip() for l in body.splitlines()
           if l.strip().lower().startswith("disallow:") and l.split(":", 1)[1].strip()]
    note = ("no robots.txt served (allowed)" if not body
            else ("no Disallow directives" if not dis
                  else "; ".join(dis[:6])))
    return allowed, note


def reach(host: str, accept=None) -> tuple[str | None, str, str]:
    """Ladder, cheapest rung first, and each rung answers a DIFFERENT question.

    A 403 is very often a user-agent filter (shard A turned two into 200s with
    browser headers); a TLS failure is usually a certificate that covers only
    the apex or only www (crit-nsn.gov); a DNS/connect failure is the only
    thing a www flip can fix. Trying all sixteen combinations on every host
    cost 16 requests where 2 answer, so each rung is now tried only against
    the failure shape it actually addresses.

    `accept(body)` is a validator. THE FIRST HTTP 200 IS NOT NECESSARILY THE
    SITE: redlakenation.org serves a 689-byte IIS7 placeholder at the apex and
    the real site is on www. Without a validator the ladder stopped at the
    stub, the name check refused it, and Red Lake was dropped. Where the
    validator refuses a rung, the ladder KEEPS GOING and only reports the
    refusal if every rung fails.

    Returns (root, how, body). The BODY MATTERS: the first version re-fetched
    the homepage to run the name check and, where the second fetch behaved
    differently from the rung that worked, read an empty string and recorded
    "does not name the entity" — thirteen real tribal sites, Red Lake,
    Menominee, San Carlos and Standing Rock among them, deleted from the sweep
    by a check that never saw the page. Judge the bytes that actually
    answered.
    """
    alt = host[4:] if host.startswith("www.") else "www." + host
    best = None
    for cand in (host, alt):
        if is_excluded(cand):
            return None, "excluded", ""
        for scheme in ("https", "http"):
            root = f"{scheme}://{cand}"
            r = fetch(root, headers=HEADERS)
            if r["status"] in ("EXCLUDED", "RUN_DEADLINE"):
                return None, str(r["status"]), ""
            if r["ok"] and r["status"] < 400 and r["text"]:
                if accept is None or accept(r["text"]):
                    return root, f"{scheme}, {cand}, our UA", r["text"]
                best = best or (root, f"{scheme}, {cand}, our UA", r["text"])
                continue
            if r["ok"] and r["status"] in (401, 403, 406, 429, 503):
                r2 = fetch(root, headers=BROWSER_HEADERS)
                if r2["ok"] and r2["status"] < 400 and r2["text"]:
                    if accept is None or accept(r2["text"]):
                        return (root, f"{scheme}, {cand}, browser headers",
                                r2["text"])
                    best = best or (root, f"{scheme}, {cand}, browser headers",
                                    r2["text"])
            if not r["ok"] and "SSL" in str(r["status"]):
                r3 = fetch(root, headers=BROWSER_HEADERS, verify=False)
                if r3["ok"] and r3["status"] < 400 and r3["text"]:
                    if accept is None or accept(r3["text"]):
                        return (root, f"{scheme}, {cand}, relaxed TLS",
                                r3["text"])
                    best = best or (root, f"{scheme}, {cand}, relaxed TLS",
                                    r3["text"])
            if not r["ok"] and str(r["status"]) in (
                    "ConnectionError", "ConnectTimeout", "Timeout",
                    "ReadTimeout"):
                continue                     # try http, then the www flip
            if r["ok"]:
                break                        # a real HTTP answer; http:// adds nothing
    if best:
        return best[0], best[1] + " (page does not name the entity)", best[2]
    return None, "unreachable by every rung", ""


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------

def classify(blob: str) -> tuple[str | None, str]:
    """Return (kind, matched_term) where kind is enterprise_register /
    member_business_list / None. NOTALIST wins over both."""
    text = blob or ""
    m_ent = ENTERPRISE_PAT.search(text)
    m_mem = MEMBERLIST_PAT.search(text)
    if not (m_ent or m_mem):
        return None, ""
    if NOTALIST_PAT.search(text):
        return None, ""
    if m_ent:
        return "enterprise_register", m_ent.group(0)
    return "member_business_list", m_mem.group(0)


def names_entity(html: str, canonical: str) -> str:
    """The page must NAME THE ENTITY. Returns 'YES: tok' / 'NO' / 'HIJACK'."""
    # Scan the WHOLE document. A 200,000-character cap read
    # menominee-nsn.gov - 321 KB, titled "MITW - Home Page" - as not naming
    # the Menominee, because the word first appears past the cap. A truncated
    # read that reports "absent" rather than "truncated" is the same defect
    # PULL_DISCIPLINE.md records for PDFs.
    low = (html or "").lower()
    if HIJACK_PAT.search(low):
        return "HIJACK"
    toks = [t for t in re.split(r"[^a-z]+", (canonical or "").lower())
            if len(t) >= 4 and t not in {
                "tribe", "band", "nation", "indian", "indians", "pueblo",
                "community", "rancheria", "reservation", "confederated",
                "tribes", "village", "council", "peoples", "people"}]
    for t in toks:
        if t in low:
            return "YES: " + t
    # A page may print the name with the spaces closed up — "RedLakeNation",
    # "SanCarlosApache" — or hyphenated in a logo alt. Strip every non-letter
    # from the served bytes and look again. Cheap, and it is the difference
    # between recording a real tribal site and deleting it from the sweep.
    flat = re.sub(r"[^a-z]", "", low)
    for t in toks:
        if len(t) >= 5 and t in flat:
            return "YES(flattened): " + t
    joined = "".join(toks[:3])
    if len(joined) >= 6 and joined in flat:
        return "YES(flattened): " + joined
    # single short name (Kaw, Ute, Sac) — fall back to the raw phrase
    ph = re.sub(r"[^a-z ]+", " ", (canonical or "").lower()).strip()
    if ph and ph in low:
        return "YES: " + ph
    return "NO"


# ---------------------------------------------------------------------------
# targets
# ---------------------------------------------------------------------------

def uid_map() -> dict[str, str]:
    m = {}
    if SPINE.exists():
        with open(SPINE, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if r.get("tribe_id") and r.get("cedar_uid"):
                    m[r["tribe_id"]] = r["cedar_uid"]
    return m


def targets() -> list[dict]:
    uids = uid_map()
    out = []
    with open(REGISTRY, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            site = (r.get("official_site") or "").strip()
            hosts = [_bare(h) for h in (r.get("hosts") or "").split(";") if h.strip()]
            if site:
                hosts.insert(0, _bare(site))
            hosts = [h for h in dict.fromkeys(hosts) if h]
            if not hosts:
                continue
            out.append({
                "tribe_id": r["tribe_id"],
                "tribe_cedar_uid": uids.get(r["tribe_id"], ""),
                "canonical_name": r["canonical_name"],
                "state": r.get("state", ""),
                "prior_verdict": r.get("verdict", ""),
                "prior_checked_by": r.get("checked_by", ""),
                "host": hosts[0],
                "all_hosts": hosts,
            })
    return out


# ---------------------------------------------------------------------------
# STAGE: offline — zero network
# ---------------------------------------------------------------------------

def stage_offline() -> list[dict]:
    hits = []
    seen = set()

    def emit(**kw):
        key = (kw.get("canonical_name"), kw.get("url"))
        if key in seen:
            return
        seen.add(key)
        hits.append(kw)

    # 1. shard M media inventory, rescanned with the new vocabulary
    inv = HARVEST / "shard_m" / "media_inventory.csv"
    n_media = 0
    if inv.exists():
        with open(inv, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                n_media += 1
                blob = f"{r.get('source_url','')} {r.get('title','')}"
                kind, term = classify(blob)
                if kind:
                    emit(cedar_uid=r.get("cedar_uid", ""),
                         canonical_name=r.get("canonical_name", ""),
                         host=r.get("host", ""), url=r.get("source_url", ""),
                         title=re.sub(r"&#\d+;", "'", r.get("title", "")),
                         kind=kind, matched=term,
                         edition_date=(r.get("date") or "")[:10],
                         technique="offline re-read of shard_m media_inventory.csv "
                                   "(HIDDEN_DATA_TECHNIQUES #3, zero requests)")

    # 2. every recorded custom post type from shards L and M
    n_cpt = 0
    def cpts(slugs, name, host, uid):
        nonlocal n_cpt
        for s in slugs or []:
            if s in CPT_SKIP:
                continue
            n_cpt += 1
            kind, term = classify(s.replace("_", " ").replace("-", " "))
            if kind:
                emit(cedar_uid=uid, canonical_name=name, host=host,
                     url=f"https://{host}/wp-json/wp/v2/{s}?per_page=100",
                     title=f"custom post type `{s}`", kind=kind, matched=term,
                     edition_date="",
                     technique="offline re-read of shard L/M recorded "
                               "wp/v2/types (HIDDEN_DATA_TECHNIQUES #3)")

    for f in glob.glob(str(HARVEST / "shard_l" / "probe*.jsonl")):
        for line in open(f, encoding="utf-8"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            cpts(d.get("post_types"), d.get("canonical_name", ""),
                 d.get("host", ""), d.get("cedar_uid", ""))
    hm = HARVEST / "shard_m" / "host_log.jsonl"
    if hm.exists():
        for line in open(hm, encoding="utf-8"):
            d = json.loads(line)
            cpts(d.get("wp_types"), d.get("canonical_name", ""),
                 d.get("host", ""), d.get("cedar_uid", ""))
    dp = HARVEST / "shard_m" / "deep_probe.jsonl"
    if dp.exists():
        for line in open(dp, encoding="utf-8"):
            d = json.loads(line)
            cpts(d.get("cpts"), d.get("canonical_name", ""),
                 d.get("host", ""), d.get("cedar_uid", ""))

    print(f"[offline] media rows rescanned {n_media}; cpt slugs rescanned "
          f"{n_cpt}; candidate hits {len(hits)}", flush=True)
    return hits


# ---------------------------------------------------------------------------
# STAGE: online — one host at a time
# ---------------------------------------------------------------------------

def sweep_host(t: dict) -> dict:
    host = t["host"]
    log = {
        "tribe_id": t["tribe_id"], "tribe_cedar_uid": t["tribe_cedar_uid"],
        "canonical_name": t["canonical_name"], "host": host,
        "checked_date": TODAY, "prior_verdict": t["prior_verdict"],
        "excluded_reason": "", "robots_note": "", "robots_allowed": None,
        "reached": "N", "reach_route": "", "names_entity": "",
        "terms_status": "NOT_CHECKED", "terms_url": "", "terms_quote": "",
        "wp": "N", "cpts": [], "media_total": 0, "media_scanned": 0,
        "search_ran": False, "sitemap_urls": 0, "hits": [],
        "routes": {"types": False, "search": False, "media": False,
                   "sitemap": False},
        "machine_readable_basis": "",
        "requests": 0, "errors": [],
    }
    r0 = _nreq[0]

    why = is_excluded(host)
    if why:
        log["excluded_reason"] = why
        log["terms_status"] = "TERMS_STATED_RESTRICTIVE"
        return log

    root, how, body = reach(
        host, accept=lambda b: names_entity(b, t["canonical_name"]) != "NO")
    log["reach_route"] = how
    if not root:
        log["requests"] = _nreq[0] - r0
        return log
    log["reached"] = "Y"

    # 1 -- robots, with OUR UA
    ok, note = robots_ok(root)
    log["robots_allowed"], log["robots_note"] = ok, note
    if not ok:
        log["errors"].append("robots Disallow on /")
        log["requests"] = _nreq[0] - r0
        return log

    # 2 -- the page must name the entity. Judge the bytes reach() already got.
    log["names_entity"] = names_entity(body, t["canonical_name"])
    if log["names_entity"] != "YES" and not log["names_entity"].startswith("YES"):
        log["errors"].append(
            "served page does not name the entity — not treated as this "
            "tribe's site (six hijacked tribal domains found 2026-09-01)")
        log["requests"] = _nreq[0] - r0
        return log

    # 3 -- TERMS, BEFORE any enumeration
    for p in TERMS_PATHS:
        r = fetch(root + p, headers=BROWSER_HEADERS, verify=False)
        if not (r["ok"] and r["status"] == 200 and len(r["text"]) > 400):
            continue
        txt = re.sub(r"<[^>]+>", " ", r["text"])
        m = TERMS_FORBID_PAT.search(txt)
        log["terms_url"] = r["url"]
        if m:
            s = max(0, m.start() - 130)
            quote = re.sub(r"\s+", " ", txt[s:m.end() + 130]).strip()
            log["terms_quote"] = quote
            if MARK_CONTEXT_PAT.search(quote):
                # a trademark notice, not a data-reuse restriction
                log["terms_status"] = "TERMS_STATED_COPYRIGHT_ONLY"
            else:
                log["terms_status"] = "TERMS_STATED_RESTRICTIVE"
                log["requests"] = _nreq[0] - r0
                return log                   # nothing further is requested
        else:
            log["terms_status"] = "TERMS_READ_PERMISSIVE"
        break
    else:
        log["terms_status"] = "NO_TERMS_PAGE_SERVED"

    def note_hit(route, url, title, extra=""):
        kind, term = classify(f"{url} {title} {extra}")
        if not kind:
            return
        log["hits"].append({"route": route, "url": url,
                            "title": title.strip()[:200], "kind": kind,
                            "matched": term})

    # 4 -- CUSTOM POST TYPES. Highest-yield signal; both prior finds came here.
    #      One cheap probe gates the three WordPress routes. On a host with no
    #      REST API the media/search/types calls all 404 for the same reason,
    #      and paying for them three times over 359 hosts is the difference
    #      between a 30-minute run and a 90-minute one. If /wp-json does not
    #      answer, the honest record is that those routes DO NOT EXIST here,
    #      which is what `machine_readable_basis` says.
    probe = fetch(f"{root}/wp-json/", headers=BROWSER_HEADERS, verify=False)
    has_wp = bool(probe["ok"] and probe["status"] == 200
                  and probe["text"].lstrip().startswith("{"))
    log["machine_readable_basis"] = (
        "WordPress REST answered; types/search/media all attempted" if has_wp
        else "not WordPress - /wp-json returns nothing, so the media index, "
             "custom post types and REST search DO NOT EXIST on this host; "
             "the only machine-readable route is the sitemap")
    r = ({"ok": False, "status": 0, "text": "", "headers": {}} if not has_wp
         else fetch(f"{root}/wp-json/wp/v2/types", headers=BROWSER_HEADERS,
                    verify=False))
    if r["ok"] and r["status"] == 200:
        try:
            types = json.loads(r["text"])
        except ValueError:
            types = {}
        if isinstance(types, dict) and types:
            log["wp"] = "Y"
            log["routes"]["types"] = True
            for slug, meta in types.items():
                if slug in CPT_SKIP or not isinstance(meta, dict):
                    continue
                log["cpts"].append(slug)
                label = f"{meta.get('name','')} {slug}".replace("_", " ")
                kind, term = classify(label)
                if not kind:
                    continue
                base = meta.get("rest_base") or slug
                ep = f"{root}/wp-json/wp/v2/{base}?per_page=100"
                log["hits"].append({"route": "custom_post_type", "url": ep,
                                    "title": f"CPT `{slug}` "
                                             f"({meta.get('name','')})",
                                    "kind": kind, "matched": term})
                rr = fetch(ep, headers=BROWSER_HEADERS, verify=False)
                if rr["ok"] and rr["status"] == 200:
                    try:
                        items = json.loads(rr["text"])
                    except ValueError:
                        items = []
                    if isinstance(items, list):
                        fn = RAW / f"{t['tribe_id']}_{base}_cpt.json"
                        RAW.mkdir(parents=True, exist_ok=True)
                        fn.write_text(rr["text"][:4_000_000],
                                      encoding="utf-8")
                        log["hits"][-1]["n_items"] = len(items)
                        log["hits"][-1]["raw_file"] = fn.name

    # 5 -- REST search with the TERO-free terms
    for term in (SEARCH_TERMS if has_wp else []):
        r = fetch(f"{root}/wp-json/wp/v2/search?search={up.quote(term)}"
                  f"&per_page=100", headers=BROWSER_HEADERS, verify=False)
        if not (r["ok"] and r["status"] == 200):
            continue
        log["routes"]["search"] = True
        log["search_ran"] = True
        log["wp"] = "Y"
        try:
            items = json.loads(r["text"])
        except ValueError:
            continue
        for it in items if isinstance(items, list) else []:
            note_hit("rest_search", str(it.get("url", "")),
                     f"[{term}] {it.get('title','')}")

    # 6 -- MEDIA, UNFILTERED BY MIME (shard M's best find was a .docx)
    page, total_pages, seen = 1, 1, 0
    while has_wp and page <= total_pages and page <= MEDIA_PAGE_CAP:
        r = fetch(f"{root}/wp-json/wp/v2/media?per_page=100&page={page}"
                  f"&_fields=source_url,title,date,modified,mime_type",
                  headers=BROWSER_HEADERS, verify=False)
        if not (r["ok"] and r["status"] == 200):
            break
        try:
            items = json.loads(r["text"])
        except ValueError:
            break
        if not isinstance(items, list) or not items:
            break
        log["wp"] = "Y"
        log["routes"]["media"] = True
        log["media_total"] = int(r["headers"].get("x-wp-total", 0) or 0)
        total_pages = int(r["headers"].get("x-wp-totalpages", 1) or 1)
        for it in items:
            seen += 1
            title = re.sub(r"<[^>]+>", "",
                           (it.get("title") or {}).get("rendered", ""))
            u = it.get("source_url", "") or ""
            mime = it.get("mime_type", "") or ""
            kind, term = classify(f"{u} {title}")
            # ENUMERATE unfiltered - shard M's best find was a .docx and a
            # PDF-only filter would have missed it - but a business LIST is
            # never a photograph. The filter is on what may be a list, not on
            # what may be fetched.
            if kind and not mime.startswith(("image/", "video/", "audio/")):
                log["hits"].append({
                    "route": "wp_media", "url": u, "title": title.strip()[:200],
                    "kind": kind, "matched": term,
                    "edition_date": (it.get("date") or "")[:10],
                    "modified": (it.get("modified") or "")[:10],
                    "mime": mime})
        page += 1
    log["media_scanned"] = seen

    # 7 -- sitemaps
    locs = []
    for sm in ("/sitemap_index.xml", "/sitemap.xml", "/wp-sitemap.xml"):
        r = fetch(root + sm, headers=BROWSER_HEADERS, verify=False)
        if not (r["ok"] and r["status"] == 200 and "<" in r["text"]):
            continue
        log["routes"]["sitemap"] = True
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r["text"])
        for sub in [l for l in locs if l.endswith(".xml")][:6]:
            r2 = fetch(sub, headers=BROWSER_HEADERS, verify=False)
            if r2["ok"] and r2["status"] == 200:
                locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r2["text"])
        break
    pages = [l for l in dict.fromkeys(locs) if not l.endswith(".xml")]
    log["sitemap_urls"] = len(pages)
    for l in pages:
        if PATH_PAT.search(up.urlparse(l).path):
            kind, term = classify(up.urlparse(l).path.replace("/", " "))
            if kind:
                log["hits"].append({"route": "sitemap", "url": l, "title": "",
                                    "kind": kind, "matched": term})

    log["requests"] = _nreq[0] - r0
    return log



# ---------------------------------------------------------------------------
# STAGE: build the ENTERPRISE REGISTER
#
# A nation listing its own subsidiaries is PARENT-ASSERTED OWNERSHIP, the
# strongest evidence class in this project — the class shard E used for 482 ANC
# edges, 355 of them from audited filings. It feeds the HUB / SUB-HUB crosswalk
# in docs/IDENTIFIER_STANDARD.md, not the vendor dataset: Ho-Chunk Inc is a
# sub-hub of the Winnebago Tribe, and the tribe's own enterprise page is the
# cleanest statement of that relationship available.
#
# IDENTITY IS NOT RESOLVED HERE. Every candidate match carries a confidence and
# a method and stays a candidate. Nothing is minted; nothing reaches the spine.
# ---------------------------------------------------------------------------

# The identity_scope gradient in data/clean/native_owned_businesses.csv must
# not be flattened. Bad River publishes 31 tribally-owned firms AND 8 area
# businesses in two tables; flattening would have converted eight non-Native
# local firms into Native-owned ones.
SCOPE_BY_KIND = {
    "enterprise_register": "tribally_owned_entity",   # the nation owns it
    "member_business_list": "any_native",             # a member owns it
    "licence_register": "unknown",                    # licensed, not owned
    "vendor_list": "vendor_relationship",             # may own nothing
}

REL_HINT = [
    (re.compile(r"joint[\s\-]*venture|\bJV\b|partnership with", re.I),
     "joint_venture"),
    (re.compile(r"passive (investment|holding)|investment portfolio|"
                r"minority (stake|interest)", re.I), "passive_investment"),
    (re.compile(r"\bdivision\b|\bdepartment\b|\bprogram(me)?\b", re.I),
     "division"),
    (re.compile(r"subsidiar", re.I), "subsidiary"),
]


def relationship_for(name: str, context: str) -> str:
    for pat, rel in REL_HINT:
        if pat.search(f"{name} {context}"):
            return rel
    return "wholly_owned"


def _norm(n: str) -> str:
    n = re.sub(r"[^a-z0-9 ]+", " ", (n or "").lower())
    n = re.sub(r"\b(inc|llc|l l c|corp|corporation|company|co|ltd|the|"
               r"incorporated|limited|lp|llp|plc)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def cedar_name_index() -> dict[str, list[tuple[str, str, str]]]:
    """normalized name -> [(entity_id, entity_name, table)]  — CANDIDATES only."""
    idx: dict[str, list[tuple[str, str, str]]] = {}

    def put(name, eid, src):
        k = _norm(name)
        if len(k) < 5:
            return                      # a generic fragment may not win a match
        idx.setdefault(k, []).append((eid or "", name, src))

    for path, ncol, icol, src in [
        (ROOT / "data" / "spine" / "cedar_entity_spine.csv",
         "canonical_name", "cedar_entity_id", "spine"),
        (ROOT / "data" / "clean" / "entity_aliases.csv",
         "alias_name", "entity_id", "entity_aliases"),
        (ROOT / "data" / "clean" / "native_owned_businesses.csv",
         "business_name_raw", "business_entity_id", "native_owned_businesses"),
        (ROOT / "data" / "clean" / "individual_native_firm_register.csv",
         "firm_name", "entity_id", "individual_native_firm_register"),
    ]:
        if not path.exists():
            continue
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            if ncol not in (rd.fieldnames or []):
                continue
            for r in rd:
                put(r.get(ncol, ""), r.get(icol, ""), src)
    return idx


GENERIC_NAME = {
    "cultural", "culture", "history", "casino", "corporation", "enterprise",
    "enterprises", "holdings", "commerce", "economic development",
    "travel center", "gaming", "housing", "health", "education", "tribal",
    "business", "businesses", "tribal business", "tribal businesses",
    "tribal enterprises", "our enterprises", "philanthropy", "directory",
}


def match_candidate(name: str, idx) -> dict:
    """ENTITY_MATCH_RULES checklist step 1-2. Exact normalized name only.

    Containment and token-subset are WEAK classes and rule 9 refuses them
    without a second independent signal, which a name on a web page does not
    supply. So this proposes exact-normalized matches and nothing else, and
    every one is a CANDIDATE with a confidence — never a resolution.
    """
    k = _norm(name)
    # ENTITY_MATCH_RULES rule 1: an entity whose entire distinctive token set
    # is generic may not win a match that rests only on the name. Measured
    # here: the single word "Cultural", scraped from Cahuilla's department
    # nav, matched Southern Ute through a one-token `brand` alias - the
    # identical defect the rule was written from, reproduced by this pass.
    if len(k.split()) < 2 or k in GENERIC_NAME:
        return {"candidate_cedar_entity_id": "", "candidate_cedar_name": "",
                "candidate_source_table": "", "match_method": "refused_generic",
                "match_confidence": 0.0,
                "match_note": "whole name is generic - rule 1 refuses a "
                              "name-only match"}
    hits = idx.get(k, [])
    if not hits:
        return {"candidate_cedar_entity_id": "", "candidate_cedar_name": "",
                "candidate_source_table": "", "match_method": "none",
                "match_confidence": 0.0}
    eids = {h[0] for h in hits if h[0]}
    tables = ";".join(sorted({h[2] for h in hits}))
    if not eids:
        # Cedar has SEEN this name and never keyed it. That is a different
        # fact from "Cedar does not know it", and reporting it as a 0.5 match
        # with a blank id would put a confidence on nothing.
        return {"candidate_cedar_entity_id": "",
                "candidate_cedar_entity_ids": "",
                "candidate_cedar_name": hits[0][1],
                "candidate_source_table": tables,
                "match_method": "name_present_in_cedar_but_unkeyed",
                "match_confidence": 0.0,
                "match_note": "the name appears in Cedar with no entity_id"}
    conf = 0.80 if len(eids) == 1 else 0.40
    return {"candidate_cedar_entity_ids": ";".join(sorted(eids)),
            "candidate_cedar_entity_id": sorted(eids)[0],
            "candidate_cedar_name": hits[0][1],
            "candidate_source_table": tables,
            "match_method": "exact_normalized_name",
            "match_confidence": conf,
            "match_note": ("" if len(eids) == 1 else
                           f"{len(eids)} Cedar entities share this normalized "
                           f"name — AMBIGUOUS, do not resolve")}


_HOSTKEY: dict[str, tuple[str, str]] = {}


def build_hostkey(uids: dict[str, str]) -> None:
    """host -> (tribe_id, cedar_uid), from the registry's own host columns."""
    _HOSTKEY.clear()
    with open(REGISTRY, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            tid = r.get("tribe_id", "")
            for h in ([r.get("official_site", "")]
                      + (r.get("hosts", "") or "").split(";")):
                b = _bare(h)
                if b:
                    _HOSTKEY.setdefault(b, (tid, uids.get(tid, "")))


def tribe_key_index() -> dict[str, tuple[str, str]]:
    """normalized tribe name -> (tribe_id, cedar_uid). For the hub side."""
    idx = {}
    if SPINE.exists():
        with open(SPINE, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                for nm in (r.get("canonical_name"), r.get("fr_official_name")):
                    k = _norm(nm or "")
                    if k:
                        idx.setdefault(k, (r.get("tribe_id", ""),
                                           r.get("cedar_uid", "")))
    return idx


def resolve_hub(row: dict, tidx: dict) -> None:
    """Fill tribe_id / tribe_cedar_uid from a `bia:slug` or a display name.

    The HUB side is the easy half — the publisher of an enterprise register is
    the nation whose site it is, and we already know which tribe we asked. This
    only has to recover the key for the shard-L rows, which carry a `nation_id`
    slug instead of a Cedar id.
    """
    if row.get("tribe_cedar_uid") and row.get("tribe_id"):
        return
    # The strongest hub route is not a name at all: the register was published
    # ON that nation's own site, and the registry already records which host
    # belongs to which tribe. Use that before any name inference.
    h = _bare(up.urlparse(row.get("source_url", "") or "").netloc)
    if h and h in _HOSTKEY:
        row["tribe_id"], row["tribe_cedar_uid"] = _HOSTKEY[h]
        row["hub_match_method"] = "publisher_host_in_registry"
        return
    name = row.get("tribe_name", "") or ""
    if ":" in name:
        name = name.split(":", 1)[1].replace("-", " ")
    for k in (_norm(name),
              _norm(re.sub(r"\b(tribe|nation|band|of|the|indians|"
                           r"confederated|corporation|limited|regional)\b",
                           " ", name))):
        if k and k in tidx:
            row["tribe_id"], row["tribe_cedar_uid"] = tidx[k]
            row["hub_match_method"] = "normalized_tribe_name"
            return
    row.setdefault("hub_match_method", "unresolved")



# A heading scrape reaches the page's furniture as well as its content, and no
# amount of tuning removes the last of it. So every HTML-derived row carries a
# `review_status`, and only rows that clear this test are counted. A CPT
# collection is one post per enterprise, written by the nation, and is
# accepted on that basis alone.
NAV_FURNITURE = re.compile(
    r"^(economic development|corporation|culture|history|philanthropy|"
    r"casino|travel center|committees|delegates|phone|fax|instagram|"
    r"linkedin|facebook|twitter|meetings|members needed|employment|health|"
    r"public health|healthy living|emergency management|veterans|present|"
    r"pre-contact|tribal story|directory|announcements|covid-19|"
    r"land acknowledgement statements|economic impact|meet our staff|"
    r"accept|reject|privacy overview|necessary|non-necessary|"
    r"employment & training|community investment|our tribal enterprises|"
    r"epic events|retail shop|bingo|tribally-owned and operated|"
    r"job opportunities|job request form|employee performance review|tero|"
    r"contractors? business (application|form)|indian preference plan|"
    r"weekly labor force report|vendor application|"
    r"salmon festival vendor application|propose a project|"
    r"please contact us for more information|tribal member login|"
    r"cultural|ccvap|aswet|terc|youth and family|sorna|"
    r"tribal health programs|crow tribal govt\.?|tribal businesses|"
    r"business insider article|website by .*)\W*$", re.I)


# A HUB CANNOT BE ITS PEER'S SUBSIDIARY.
# Doyon's own operating-companies page names HUNA TOTEM CORPORATION and
# KLAWOCK HEENYA CORPORATION. Cedar keys both as Alaska Native VILLAGE
# corporations in their own right (ANVC-HUNATO-00, ANVC-KLWCKH-00), and
# ANCSA_OWNERSHIP_RULING does not let a regional corporation own a village
# corporation. Doyon is telling the truth about a RELATIONSHIP and the shape
# is a joint venture - the Alaska tourism JVs - which ENTITY_MATCH_RULES
# rule 11 says genuinely has two parents. Taking the page at face value would
# have converted two independent ANCSA corporations into subsidiaries, which
# is the ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION family of defect
# reached from a new direction.
#
# So: where the named firm resolves to a Cedar HUB that is not this publisher,
# the row is HELD and its relationship downgraded. This is the contradiction
# class the workstream was asked to surface, and it is a general predicate,
# not a fix for two rows.
HUB_PREFIX = ("ANVC-", "ANRC-", "TRBF-", "AKNF-", "CNSF-", "NHOF-")


def contradicts_a_hub(row: dict) -> str:
    # Check EVERY candidate id, not the alphabetically first. Huna Totem
    # matched both `A-0018` (a native_owned_businesses row) and
    # `ANVC-HUNATO-00` (the village corporation hub); sorting put the
    # non-hub first and the contradiction would have been missed.
    ids = (row.get("candidate_cedar_entity_ids", "")
           or row.get("candidate_cedar_entity_id", "") or "").split(";")
    for cid in ids:
        if cid and cid.startswith(HUB_PREFIX) and cid != row.get("tribe_id"):
            return cid
    return ""


def review_status(row: dict) -> tuple[str, str]:
    nm = row.get("enterprise_name_raw", "")
    hub = contradicts_a_hub(row)
    if hub:
        return ("held_contradicts_cedar",
                f"the named firm resolves to Cedar hub {hub}, a separate "
                f"entity - a hub is never its peer's subsidiary; treat as a "
                f"joint venture or a partner, not ownership")
    if "custom post type" in (row.get("extraction_note", "") or ""):
        return "accepted", "one post per enterprise in the nation's own CPT"
    if NAV_FURNITURE.match(nm):
        return "held_nav_furniture", "site navigation or a section label"
    if re.search(r"\bWEBSITE\b|\barticle\b", nm):
        return "held_nav_furniture", "a link label, not a firm name"
    if len(nm.split()) == 1 and not re.search(r"(LLC|Inc|Corp|Co)\.?$", nm):
        return "held_single_generic_word", "one generic word cannot name a firm"
    return "accepted", "named on the nation's own enterprise page"


def stage_build_register(rows: list[dict]) -> int:
    """rows: dicts already carrying the register fields. Writes JSONL."""
    idx = cedar_name_index()
    tidx = tribe_key_index()
    build_hostkey(uid_map())
    n = 0
    with open(ENTERPRISE_JSONL, "a", encoding="utf-8") as fh:
        for r in rows:
            out = dict(r)
            resolve_hub(out, tidx)
            out.update(match_candidate(r["enterprise_name_raw"], idx))
            out.setdefault("identity_scope",
                           SCOPE_BY_KIND["enterprise_register"])
            out.setdefault("assertion_class", "OWNERSHIP")
            out.setdefault("record_scope", "BUSINESS")
            out.setdefault("population_basis",
                           "spine_federally_recognized_tribe")
            out.setdefault("built_by_script",
                           "code/701_enterprise_and_business_list_sweep.py")
            st, why = review_status(out)
            if st == "held_contradicts_cedar":
                out["relationship"] = "joint_venture"
                out["contradicts_cedar_entity_id"] =                     out.get("candidate_cedar_entity_id", "")
            out["review_status"] = st
            out["review_status_basis"] = why
            out.setdefault("resolved", False)
            fh.write(json.dumps(out, ensure_ascii=False) + "\n")
            n += 1
    return n



# --- collectors: where enterprise rows come from -----------------------------

BUSREG = ROOT / "data" / "staging" / "business_registry"


def collect_from_shard_l() -> list[dict]:
    """Shard L's already-harvested enterprise registers, restated in the
    hub/sub-hub schema.

    These are NOT new finds and are counted separately. They are here because
    `enterprise_register.jsonl` is meant to be the complete parent-asserted
    ownership table for the crosswalk, and a table that omits the six registers
    a sibling already harvested is not one. Provenance names shard L.
    """
    rows = []
    for path in sorted(BUSREG.glob("*.jsonl")):
        recs = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    recs.append(json.loads(line))
                except ValueError:
                    pass
        if not recs or recs[0].get("directory_type") != "subsidiary_directory":
            continue
        for r in recs:
            claim = r.get("identity_claim_text", "") or ""
            rows.append({
                "tribe_cedar_uid": "",          # filled by tribe_name below
                "tribe_id": "",
                "tribe_name": (r.get("certifying_authority_name")
                               or r.get("nation_id", "")),
                "enterprise_name_raw": r.get("business_name_raw", ""),
                "relationship": relationship_for(
                    r.get("business_name_raw", ""),
                    claim + " " + " ".join(r.get("validation_flags") or [])),
                "sector": r.get("service_category_raw") or "",
                "source_url": r.get("source_url", ""),
                "source_id": r.get("source_id", ""),
                # TBD-056 and TBD-059 carry no harvest_date. Shard L ran on
                # 2026-09-01, which is the honest floor, and the field is
                # flagged so a null is never mistaken for a measurement.
                "retrieved_date": r.get("harvest_date") or "2026-09-01",
                "retrieved_date_basis": ("source harvest_date"
                                         if r.get("harvest_date")
                                         else "source carried none; shard L "
                                              "ran 2026-09-01"),
                "source_edition_date": (r.get("source_edition")
                                        or r.get("source_last_updated") or ""),
                "quote": claim[:600],
                "technique": ("harvested by shard L 2026-09-01; restated here "
                              "in the hub/sub-hub schema by script 701"),
                "discovered_by": "shard-L",
                "identity_scope": r.get("identity_scope",
                                        "tribally_owned_entity"),
            })
    return rows


def collect_from_cpt_raw() -> list[dict]:
    """Enterprise CPT collections this sweep fetched, in raw/*_cpt.json."""
    rows = []
    if not RAW.exists():
        return rows
    hostmap = {}
    if HOSTLOG.exists():
        for line in HOSTLOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            hostmap[d["tribe_id"]] = d
    for f in sorted(RAW.glob("*_cpt.json")):
        tribe_id = f.name.split("_")[0]
        meta = hostmap.get(tribe_id, {})
        try:
            items = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(items, list):
            continue
        cpt = f.name[len(tribe_id) + 1:-len("_cpt.json")]
        kind, _ = classify(cpt.replace("_", " ").replace("-", " "))
        if kind != "enterprise_register":
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            name = re.sub(r"<[^>]+>", "",
                          (it.get("title") or {}).get("rendered", "")).strip()
            if not name:
                continue
            excerpt = re.sub(r"<[^>]+>", " ",
                             (it.get("excerpt") or {}).get("rendered", ""))
            excerpt = re.sub(r"\s+", " ", excerpt).strip()
            rows.append({
                "tribe_cedar_uid": meta.get("tribe_cedar_uid", ""),
                "tribe_id": tribe_id,
                "tribe_name": meta.get("canonical_name", ""),
                "enterprise_name_raw": name,
                "relationship": relationship_for(name, excerpt),
                "sector": "",
                "source_url": it.get("link") or
                              f"https://{meta.get('host','')}/wp-json/wp/v2/"
                              f"{cpt}?per_page=100",
                "source_id": f"CE701-{tribe_id}",
                "retrieved_date": TODAY,
                "source_edition_date": (it.get("modified")
                                        or it.get("date") or "")[:10],
                "quote": (excerpt[:400] or
                          f"published by {meta.get('canonical_name','')} in a "
                          f"WordPress custom post type named `{cpt}` — the "
                          f"nation's own register of its own businesses"),
                "technique": ("HIDDEN_DATA_TECHNIQUES #3: /wp-json/wp/v2/types "
                              f"revealed custom post type `{cpt}`, then its "
                              "collection endpoint at per_page=100"),
                "discovered_by": "701 online sweep, TERO-free vocabulary",
                "identity_scope": "tribally_owned_entity",
            })
    return rows



# ---------------------------------------------------------------------------
# STAGE: adjudicate — a MENTION is not a LIST
#
# The sweep's `hits` are candidates: anything on the host whose URL or title
# carries the vocabulary. Most are not lists. A news article headlined
# "National Entrepreneurship Month", a job description for an "Enterprise
# Accountant" and a resolution amending "Title 32 Enterprise Board" all match
# the words and none of them is a register of businesses.
#
# Counting those as finds would inflate the corrected hit rate, which is the
# one number this workstream exists to produce. So the rate is computed on
# LIST_SHAPED hits only, and the weak ones are kept, labelled, and reported
# separately — never silently dropped, because a discarded candidate that
# nobody can see is indistinguishable from one that was never found.
# ---------------------------------------------------------------------------

# A phrase that names a LIST OF BUSINESSES, not a topic.
LIST_SHAPED = re.compile(
    r"(our|tribal|tribally[\s\-_]*owned|nation[\s\-_]*owned|the[\s\-_]*tribes?)"
    r"[\s\-_]*(enterprise|business|compan|subsidiar|holding)|"
    r"enterprise[sz]?[\s\-_]*(list|director|regist|roster|portfolio|page)|"
    r"(list|director|regist|roster|index)\w*[\s\-_]*of[\s\-_]*"
    r"(business|enterprise|compan|vendor|contractor)|"
    r"business[\s\-_]*(director|regist|listing|roster|guide|index)|"
    r"(member|citizen|native|indian|tribal)[\s\-_]*owned[\s\-_]*business|"
    r"certified[\s\-_]*\w*[\s\-_]*business[\s\-_]*list|"
    r"(approved|active|current|issued|licen[cs]ed)[\s\-_]*business"
    r"[\s\-_]*licen[cs]e|"
    r"business[\s\-_]*licen[cs]e[sd]?[\s\-_]*(list|regist|roster|report)|"
    r"chamber[\s\-_]*of[\s\-_]*commerce|"
    r"our[\s\-_]*(compan|enterprise|business|subsidiar)|"
    r"subsidiar(y|ies)[\s\-_]*(list|director|regist|page)?|"
    r"economic[\s\-_]*development[\s\-_]*(corp|author)",
    re.I)

NEWSISH_PATH = re.compile(
    r"/(news|stories|story|press|press-release|releases|blog|article|"
    r"events?|calendar|category|tag|author|announcement|newsletter|"
    r"job|career|employment|rfp|bid|organizer|venue)s?(/|$)|/20\d\d/\d\d/",
    re.I)

BOILERPLATE_PATH = re.compile(
    r"/(privacy|privacy-policy|terms|terms-of-service|terms-of-use|legal|"
    r"disclaimer|copyright|contact|sitemap|search|accessibility|"
    r"cookie[s]?-?policy)(/|$)", re.I)

# A SHARED CMS TEMPLATE MANUFACTURES A FAKE CLUSTER.
# `/BusinessDirectoryii.aspx` surfaced on FOUR tribes at once — Quinault,
# Northern Arapaho, Quapaw and Reno-Sparks — and four independent nations do
# not adopt the same URL. It is the CivicPlus "Resource Directory" module,
# shipped with every CivicEngage site. Read from a cached copy of Northern
# Arapaho's, at zero network cost, its 32 listings are:
#   "Batterers Intervention (BIP)", "Community Health Representatives",
#   "Diabetes Program", "Ethete Child Care", "Black Coal Senior Center"
# — tribal GOVERNMENT PROGRAMMES, mixed with two enterprises ("789 Car &
# Truck Stop", "Arapahoe Ranch"). Treating it as a Native-owned business
# register would flatten programmes into firms, the same error the Bad River
# two-table case warns about. Shard M had already ruled Quinault's copy the
# same way; this generalises that ruling to the template.
# NOTE for a later pass: the page's own Category select offers a "Tribal
# Business" filter (HIDDEN_DATA_TECHNIQUES #5 — a select IS the taxonomy).
# That filtered subset MAY be a real list and is recorded as a lead.
CMS_TEMPLATE_PATH = re.compile(
    r"/businessdirectory(i+)?\.aspx|/directory\.aspx|"
    r"/resourcedirectory", re.I)

DOCUMENT_MIME = ("application/pdf", "application/msword", "text/csv",
                 "application/vnd.openxmlformats", "application/vnd.ms-",
                 "application/vnd.oasis", "text/plain", "application/rtf")


def hit_strength(h: dict) -> str:
    """STRONG (a published list) / WEAK (the words, not a list).

    THREE corrections, each from a false positive this pass produced:

    1. The REST-search hit's title carried the query term I put there
       (`[subsidiaries] Terms of Service`), so every search result for
       "subsidiaries" scored STRONG on its own query. Strip the prefix and
       judge the PATH, which is where a list lives; prose is where a mention
       lives.
    2. A news article about an enterprise is not an enterprise register.
       `coquilletribe.org/tribal-enterprise-partners-with-forest-service/`
       matched the vocabulary perfectly and is a press release. Veto
       news-shaped paths outright.
    3. Boilerplate pages — privacy policy, terms, contact — surfaced because
       the site-wide footer text is indexed. Veto them by path.
    """
    route = h.get("route", "")
    title = re.sub(r"^\[[^\]]{1,40}\]\s*", "", h.get("title", "") or "")
    url = h.get("url", "") or ""
    path = up.urlparse(url).path

    if route == "custom_post_type":
        # A CPT literally named `enterprise` / `subsidiary` / `tribalbusiness`
        # IS the register — that is how both prior finds surfaced. Require it
        # to have returned rows: an empty CPT is a plugin's leftover.
        return "STRONG" if int(h.get("n_items") or 0) >= 2 else "WEAK"

    if route == "wp_media":
        mime = h.get("mime", "") or ""
        if not mime.startswith(DOCUMENT_MIME):
            return "WEAK"
        return "STRONG" if LIST_SHAPED.search(f"{url} {title}") else "WEAK"

    # rest_search and sitemap: judge the PATH only
    if NEWSISH_PATH.search(path) or BOILERPLATE_PATH.search(path):
        return "WEAK"
    if CMS_TEMPLATE_PATH.search(path):
        return "WEAK"
    if not LIST_SHAPED.search(path):
        return "WEAK"
    # A LIST lives at a short slug — /our-enterprises/, /business-directory/,
    # /BusinessDirectory.aspx. A NEWS STORY about one lives at a sentence:
    # /tribal-enterprise-partners-with-forest-service/ (6 words),
    # /state-of-the-city-presented-by-the-pawnee-community-chamber-of-commerce/
    # (12). Both carry the vocabulary perfectly and neither is a list, and no
    # word denylist separates them — the structural fact that a slug is a
    # sentence is what does. Five tokens is the empirical cut: the longest
    # correct slug seen is /ponca-economic-development-corporation/ at four.
    last = [seg for seg in path.strip("/").split("/") if seg][-1:]
    if last and len(re.split(r"[-_+.]", re.sub(r"\.[a-z]{2,5}$", "",
                                               last[0]))) > 5:
        return "WEAK"
    return "STRONG"


def stage_adjudicate() -> None:
    # host_log.jsonl is APPEND-ONLY across runs, so a re-probed host appears
    # twice. Keep the LAST record per tribe: a retry exists because the first
    # attempt was wrong, and counting both would double a tribe in the rate.
    logs = {}
    for l in HOSTLOG.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        d = json.loads(l)
        logs[d.get("tribe_id") or d.get("host")] = d
    logs = list(logs.values())
    # the offline stage's finds count too - same vocabulary, zero requests
    offline = {}
    if CAND_JSONL.exists():
        for l in CAND_JSONL.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            d = json.loads(l)
            offline.setdefault(d.get("canonical_name", ""), []).append({
                "route": ("custom_post_type" if "wp-json" in d.get("url", "")
                          else "wp_media"),
                "url": d.get("url", ""), "title": d.get("title", ""),
                "kind": d.get("kind", ""), "mime": "application/pdf",
                "edition_date": d.get("edition_date", ""),
                "n_items": 99 if "wp-json" in d.get("url", "") else 0,
                "offline": True})

    # A HUMAN/AGENT RULING OVERRIDES THE PATTERN. enterprise_pages.csv holds
    # the per-page rulings made by reading each candidate; a NOT_A_LIST there
    # (a business-management CLASS, a discussion FORUM, a job description, the
    # Port Angeles chamber of commerce, blank application forms) is a real
    # negative and counting it would inflate the corrected rate this
    # workstream exists to produce.
    ruled = {}
    if PAGES_CSV.exists():
        with open(PAGES_CSV, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                ruled[r["tribe_id"]] = r["ruling"].strip().upper()

    rows, n_probed, n_strong, n_ent = [], 0, 0, 0
    for d in logs:
        hits = list(d.get("hits") or []) + offline.pop(d["canonical_name"], [])
        strong = [h for h in hits if hit_strength(h) == "STRONG"]
        weak = [h for h in hits if hit_strength(h) != "STRONG"]
        rul = ruled.get(d["tribe_id"], "")
        if rul == "NOT_A_LIST":
            weak, strong = weak + strong, []
        probed = (d["reached"] == "Y" and not d["excluded_reason"]
                  and d["terms_status"] != "TERMS_STATED_RESTRICTIVE"
                  and not d["errors"])
        n_probed += bool(probed)
        n_strong += bool(strong)
        ent = [h for h in strong if h["kind"] == "enterprise_register"]
        n_ent += bool(ent)
        rows.append({
            "tribe_id": d["tribe_id"], "tribe_cedar_uid": d["tribe_cedar_uid"],
            "canonical_name": d["canonical_name"], "host": d["host"],
            "probed": "Y" if probed else "N",
            "why_not_probed": (d["excluded_reason"]
                               or ("; ".join(d["errors"]) if d["errors"]
                                   else ("" if probed else d["reach_route"]))),
            "prior_verdict_tero_vocab": d["prior_verdict"],
            "ruling": rul,
            "new_verdict": ("LIST_FOUND" if strong else
                            ("MENTION_ONLY" if weak else "NO_LIST_FOUND")),
            "n_strong": len(strong), "n_weak": len(weak),
            "kinds": ";".join(sorted({h["kind"] for h in strong})),
            "routes": ";".join(sorted({h["route"] for h in strong})),
            "edition_dates": ";".join(sorted(
                {h.get("edition_date", "") for h in strong
                 if h.get("edition_date")})),
            "top_urls": " | ".join(h["url"] for h in strong[:4]),
            "machine_readable_basis": d.get("machine_readable_basis", ""),
            "media_scanned": d.get("media_scanned", 0),
            "media_total": d.get("media_total", 0),
            "requests": d.get("requests", 0),
        })
    # tribes whose ONLY evidence came from the offline re-read
    for name, hits in offline.items():
        strong = [h for h in hits if hit_strength(h) == "STRONG"]
        rows.append({
            "tribe_id": "", "tribe_cedar_uid": "", "canonical_name": name,
            "host": "", "probed": "Y",
            "why_not_probed": "", "prior_verdict_tero_vocab": "",
            "new_verdict": "LIST_FOUND" if strong else "MENTION_ONLY",
            "n_strong": len(strong), "n_weak": len(hits) - len(strong),
            "kinds": ";".join(sorted({h["kind"] for h in strong})),
            "routes": "offline_reread",
            "edition_dates": ";".join(sorted(
                {h.get("edition_date", "") for h in strong
                 if h.get("edition_date")})),
            "top_urls": " | ".join(h["url"] for h in strong[:4]),
            "machine_readable_basis": "offline re-read of owned files",
            "media_scanned": 0, "media_total": 0, "requests": 0,
        })
        n_probed += 1
        n_strong += bool(strong)

    out = OUT / "verdicts.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"[adjudicate] {len(rows)} tribes; probed {n_probed}; "
          f"LIST_FOUND {n_strong} "
          f"({100.0 * n_strong / max(n_probed, 1):.1f}% of probed); "
          f"enterprise registers {n_ent}")
    print(f"[adjudicate] wrote {out}")



# ---------------------------------------------------------------------------
# STAGE: harvest — pull the named enterprise pages and read the firms off them
#
# Only pages a human/agent has RULED an enterprise register, listed in
# enterprise_pages.csv. Nothing is fetched on a guess.
# ---------------------------------------------------------------------------

PAGES_CSV = OUT / "enterprise_pages.csv"

# Words that are a nav item, a section heading or a call to action, never a
# firm. A heading-scrape without this returns "Menu", "Contact Us" and
# "Learn More" as subsidiaries.
NOT_A_FIRM = re.compile(
    r"^(home|menu|search|contact( us)?|about( us)?|news|events?|careers?|"
    r"jobs?|login|sign in|read more|learn more|view (all|more)|"
    r"our (story|history|mission|people|team|government|community)|"
    r"tribal (council|government|court|police|health|housing|education)|"
    r"enterprises?|our enterprises|tribal enterprises|businesses|"
    r"our businesses|subsidiaries|departments?|services|resources|"
    r"quick links|footer|header|skip to (main )?content|privacy|terms|"
    r"copyright|follow us|newsletter|social( media)?|share|print|"
    r"previous|next|back|close|toggle|navigation|breadcrumb)\W*$", re.I)


# A firm name is a proper-noun phrase. These are not names, and a heading
# scrape returns all of them: contact details, calls to action, government
# organs, and sentence fragments ending in a colon.
NOT_A_NAME = re.compile(
    r"^\W*$|^[\d\W]+$|"                                  # digits/punctuation
    r"(\+?\d[\d\-. ()]{7,}|@|https?://|www\.|\.com\b|\.gov\b|\.org\b)|"
    r":\s*$|"                                             # a label, not a name
    r"^(visit|view|book|read|learn|print|download|apply|click|see|explore|"
    r"contact|call|email|follow|share|join|get|find|more|next|previous|back|"
    r"submit|register|sign|log|open|close|toggle|skip|search|menu|home)\b|"
    r"^\d+[,.]?\d*\s|square feet|award-winning|opens in a? ?new tab",
    re.I)

# Organs of the government. A nation's committees, commissions, departments
# and boards are not its enterprises, and a page that mixes them - Crow's nav
# tree, Ponca's committee index, Cahuilla's department list - would otherwise
# put "Election Board" and "Human Resources" in an ownership table.
GOV_ORGAN = re.compile(
    r"\b(council|commission|committee|department|dept\.?|board|bureau|"
    r"court|police|enrollment|human resources|finance|planning|"
    r"public works|epa|fire|justice|scholarship|election|elders|"
    r"powwow|pow wow|liquor|veterans? affairs|head start|childcare|"
    r"child care|social services|family services|administration|"
    r"housing authority|historic preservation|education|health program|"
    r"legislative|judicial|executive|policies|bylaws|articles of|"
    r"meeting|agenda|minutes|branch|officials|chairman|vice[- ]|"
    r"secretary|treasurer|president|member seated|directors)\b", re.I)


def looks_like_a_firm(t: str) -> bool:
    if NOT_A_NAME.search(t) or GOV_ORGAN.search(t):
        return False
    words = t.split()
    if not (1 <= len(words) <= 8):
        return False
    # Title Case or ALL CAPS: a firm's name is capitalised, a sentence is not
    caps = sum(1 for w in words if w[:1].isupper())
    return caps >= max(1, len(words) - 1)


def harvest_page(row: dict) -> list[dict]:
    r = fetch(row["url"], headers=BROWSER_HEADERS, verify=False)
    if not (r["ok"] and r["status"] == 200 and r["text"]):
        return []
    RAW.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", row["url"])[-90:]
    text = r["text"]

    # --- a CPT collection endpoint answers JSON, not HTML -------------------
    if "/wp-json/" in row["url"]:
        (RAW / f"{row['tribe_id']}_{slug}.json").write_text(
            text[:4_000_000], encoding="utf-8")
        try:
            items = json.loads(text)
        except ValueError:
            return []
        out = []
        for it in items if isinstance(items, list) else []:
            if not isinstance(it, dict):
                continue
            nm = re.sub(r"<[^>]+>", "",
                        (it.get("title") or {}).get("rendered", "")).strip()
            nm = re.sub(r"&(nbsp|amp|#8217|#8211|#039|rsquo|quot);", " ", nm)
            nm = re.sub(r"\s+", " ", nm).strip()
            if not nm:
                continue
            ex = re.sub(r"<[^>]+>", " ",
                        (it.get("excerpt") or {}).get("rendered", ""))
            ex = re.sub(r"\s+", " ", ex).strip()
            out.append({
                "tribe_cedar_uid": row.get("tribe_cedar_uid", ""),
                "tribe_id": row["tribe_id"],
                "tribe_name": row["canonical_name"],
                "enterprise_name_raw": nm,
                "relationship": relationship_for(nm, ex + row.get("page_note", "")),
                "sector": "",
                "source_url": it.get("link") or row["url"],
                "source_id": f"CE701-{row['tribe_id']}",
                "retrieved_date": TODAY,
                "source_edition_date": (it.get("modified")
                                        or it.get("date") or "")[:10],
                "quote": (ex[:400] or row.get("page_note", "")),
                "technique": row.get("technique", ""),
                "discovered_by": "701 online sweep, TERO-free vocabulary",
                "identity_scope": "tribally_owned_entity",
                "extraction_note": "title.rendered from the custom post type "
                                   "collection - the nation's own record, one "
                                   "post per enterprise",
            })
        return out

    # --- rendered HTML -------------------------------------------------------
    (RAW / f"{row['tribe_id']}_{slug}.html").write_text(
        text[:3_000_000], encoding="utf-8")
    html = text

    edition = ""
    for pat in (r'"dateModified"\s*:\s*"([\d\-T:+]{10,})',
                r'"datePublished"\s*:\s*"([\d\-T:+]{10,})',
                r'property="article:modified_time"\s+content="([\d\-T:+]{10,})'):
        m = re.search(pat, html)
        if m:
            edition = m.group(1)[:10]
            break

    body = html
    m = re.search(r"<main\b.*?</main>|<article\b.*?</article>", html,
                  re.S | re.I)
    if m:
        body = m.group(0)
    body = re.sub(r"<(nav|header|footer|script|style|form|aside)\b.*?</\1>",
                  " ", body, flags=re.S | re.I)

    names, seen = [], set()
    for tag, txt in re.findall(r"<(h[2-4]|a|strong)\b[^>]*>(.*?)</\1>",
                               body, re.S | re.I):
        t = re.sub(r"<[^>]+>", " ", txt)
        t = re.sub(r"&(nbsp|amp|#8217|#8211|#039|rsquo|quot|gt|lt|aacute);",
                   " ", t)
        t = re.sub(r"\s+", " ", t).strip(" –—-|·,")
        if not (3 <= len(t) <= 90) or NOT_A_FIRM.match(t):
            continue
        if t.lower() in seen or not looks_like_a_firm(t):
            continue
        seen.add(t.lower())
        names.append((tag.lower(), t))

    quote = re.sub(r"<[^>]+>", " ", body)
    quote = re.sub(r"\s+", " ", quote).strip()[:600]
    return [{
        "tribe_cedar_uid": row.get("tribe_cedar_uid", ""),
        "tribe_id": row["tribe_id"],
        "tribe_name": row["canonical_name"],
        "enterprise_name_raw": nm,
        "relationship": relationship_for(nm, row.get("page_note", "")),
        "sector": "",
        "source_url": row["url"],
        "source_id": f"CE701-{row['tribe_id']}",
        "retrieved_date": TODAY,
        "source_edition_date": edition,
        "quote": quote,
        "technique": row.get("technique", ""),
        "discovered_by": "701 online sweep, TERO-free vocabulary",
        "identity_scope": "tribally_owned_entity",
        "extraction_note": f"name read from <{tag}> on the page; HTML heading "
                           f"scrape, not a table - review before resolving",
    } for tag, nm in names]


def stage_harvest() -> None:
    if not PAGES_CSV.exists():
        print(f"[harvest] no {PAGES_CSV.name}; nothing ruled yet")
        return
    with open(PAGES_CSV, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh)
                if (r.get("ruling") or "").strip().upper() == "ENTERPRISE_REGISTER"]
    out = []
    for r in rows:
        got = harvest_page(r)
        print(f"  {r['canonical_name']:28s} {len(got):3d} names  {r['url'][:70]}")
        out.extend(got)
    n = stage_build_register(out)
    print(f"[harvest] {n} rows appended from {len(rows)} ruled pages")



# ---------------------------------------------------------------------------
# STAGE: write the verdicts back into the shared registry
#
# APPEND-ONLY, and only into columns this workstream owns. It adds ONE new
# column, `tero_free_sweep_2026-09-01`, and touches `verdict` on a row only
# where the TERO-vocabulary pass recorded an absence that this pass disproved
# — a correction, with the old value preserved in the new column so the
# earlier verdict is never silently overwritten.
# ---------------------------------------------------------------------------

NEWCOL = "tero_free_sweep_2026-09-01"


def stage_write_registry() -> None:
    vpath = OUT / "verdicts.csv"
    with open(vpath, encoding="utf-8-sig", newline="") as fh:
        verd = {r["tribe_id"]: r for r in csv.DictReader(fh) if r["tribe_id"]}
    with open(REGISTRY, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames)
        rows = list(rd)
    if NEWCOL not in cols:
        cols.append(NEWCOL)

    n_note, n_corr = 0, 0
    for r in rows:
        v = verd.get(r["tribe_id"])
        if not v:
            r.setdefault(NEWCOL, "")
            continue
        parts = [f"TERO-FREE VOCABULARY SWEEP (code/701): {v['new_verdict']}"]
        if v["probed"] != "Y":
            parts.append(f"not probed - {v['why_not_probed']}")
        else:
            parts.append(f"strong={v['n_strong']} weak={v['n_weak']}"
                         f" routes={v['routes'] or 'none'}")
            if v["edition_dates"]:
                parts.append(f"edition dates {v['edition_dates']}")
            if v["top_urls"]:
                parts.append(v["top_urls"][:400])
            parts.append(v["machine_readable_basis"][:220])
        if (v["new_verdict"] == "LIST_FOUND"
                and r["verdict"] in ("NO_LIST_FOUND", "NOT_SEARCHED_MACHINE_READABLE",
                                     "NO_LIST_FOUND_UNVERIFIED",
                                     "LIST_REFERENCED_NOT_PUBLISHED")):
            parts.append(f"CORRECTION: verdict was `{r['verdict']}` on TERO "
                         f"vocabulary; a business/enterprise list is published")
            r["verdict"] = "LIST_FOUND_TERO_FREE_VOCAB"
            n_corr += 1
        r[NEWCOL] = " | ".join(p for p in parts if p)
        n_note += 1

    bak = REGISTRY.with_name(REGISTRY.name + ".bak_2026-09-01_pre701")
    if not bak.exists():
        bak.write_bytes(REGISTRY.read_bytes())
    with open(REGISTRY, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            r.setdefault(NEWCOL, "")
            w.writerow(r)
    print(f"[registry] annotated {n_note} rows; corrected {n_corr} verdicts; "
          f"backup {bak.name}")


# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--online", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="comma-separated tribe_id")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--build-register", action="store_true")
    ap.add_argument("--adjudicate", action="store_true")
    ap.add_argument("--harvest", action="store_true")
    ap.add_argument("--write-registry", action="store_true")
    args = ap.parse_args()
    _deadline[0] = time.time() + RUN_DEADLINE_H * 3600

    excluded_hosts()
    print(f"[excl] {len(_EXCL_REASON)} hosts off limits "
          f"(single source: excluded_hosts())", flush=True)

    if args.write_registry:
        stage_write_registry()
        return

    if args.harvest:
        stage_harvest()
        return

    if args.adjudicate:
        stage_adjudicate()
        return

    if args.build_register:
        # CPT collections are harvested through enterprise_pages.csv
        # (--harvest), which is the RULED route. Adding
        # collect_from_cpt_raw() here as well double-counted every
        # CPT register. This stage carries only the shard-L restatement.
        rows = collect_from_shard_l()
        n = stage_build_register(rows)
        print(f"[register] {n} subsidiary rows written to "
              f"{ENTERPRISE_JSONL.name}")
        return

    if args.offline or not (args.offline or args.online):
        hits = stage_offline()
        with open(CAND_JSONL, "a", encoding="utf-8") as fh:
            for h in hits:
                h["stage"] = "offline"
                h["population_basis"] = "spine_federally_recognized_tribe"
                fh.write(json.dumps(h, ensure_ascii=False) + "\n")

    if args.online:
        ts = targets()
        if args.only:
            keep = {x.strip() for x in args.only.split(",")}
            ts = [t for t in ts if t["tribe_id"] in keep]
        ts = ts[args.start:]
        if args.limit:
            ts = ts[:args.limit]
        print(f"[online] {len(ts)} hosts", flush=True)
        done = 0
        with open(HOSTLOG, "a", encoding="utf-8") as fh, \
                ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for log in ex.map(sweep_host, ts):
                fh.write(json.dumps(log, ensure_ascii=False) + "\n")
                fh.flush()
                done += 1
                if log["hits"]:
                    print(f"  HIT {log['canonical_name']:38s} "
                          f"{len(log['hits']):3d} "
                          f"{sorted({h['kind'] for h in log['hits']})}",
                          flush=True)
                if done % 25 == 0:
                    print(f"  ... {done}/{len(ts)} hosts, "
                          f"{_nreq[0]} requests", flush=True)
        state = {
            "script": "code/701_enterprise_and_business_list_sweep.py",
            "run_finished": datetime.now(timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hosts_targeted": len(ts), "requests_made": _nreq[0],
            "selection_leg": "KNOWN_IDENTIFIER (registry roster = population)",
            "population_basis": "spine_federally_recognized_tribe",
            "vocabulary": "TERO-FREE business/enterprise register terms",
            "search_terms": SEARCH_TERMS,
            "excluded_hosts_n": len(_EXCL_REASON),
            "truncated_by_deadline": time.time() > _deadline[0],
        }
        prev = json.loads(STATE.read_text()) if STATE.exists() else []
        if isinstance(prev, dict):
            prev = [prev]
        prev.append(state)
        STATE.write_text(json.dumps(prev, indent=1), encoding="utf-8")
        print(json.dumps(state, indent=1))


if __name__ == "__main__":
    main()
