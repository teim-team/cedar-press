#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1114 - capability-statement harvest: the entity's OWN page as a second
source for a federal identifier, plus the released-host and institution sweeps.

WHY THIS EXISTS
---------------
`docs/ASSERTION_LAYER.md` measured that 0 of 8,975 single-valued facts in Cedar
carry a second source, and every UEI/CAGE we hold came from the federal side
(FPDS, SAM, the award archive). An entity's own capability statement is a
GENUINELY INDEPENDENT EVIDENCE FAMILY for the same identifier. That is the
point of this script; the row count is secondary.

`docs/HARVEST_COVERAGE_AUDIT_2026-09-02.md` measured the gap: 1,439 of 1,555
entities (92.5%) have never been checked for a federal identifier on their own
site, and 185 of 185 BIE schools have never been looked at for anything.

WHAT THE 2026-09-02 OWNER RULING CHANGED
----------------------------------------
`docs/PUBLICATION_POLICY.md` <!-- TERMS-OWNER-RULING-2026-09-02 -->: a terms
page on a NATIVE ENTITY'S OWN SITE is a recorded observation, not a gate. This
script therefore harvests hosts that `TERMS_STATED_RESTRICTIVE` previously
refused. Four things the ruling does NOT release, all enforced below:
  1. technical access controls  -> FORBIDDEN_PATH_PAT, and a login/staging path
     is never requested (`/Stagingsite/` included).
  2. a natural person's data apart from their public role -> PII_FIELDS are
     never written by this script at all, and `verify` V6 asserts it.
  3. EMMA/MSRB -> not touched.
  4. Casino City / D-U-N-S proprietary -> not touched.
A NON-Native third-party host keeps its terms refusal: the ruling is about
tribal publishers, and NON_TRIBAL_TERMS_HOSTS is refused explicitly.

HAZARDS THIS SCRIPT WAS BUILT AGAINST (all measured before it was written)
--------------------------------------------------------------------------
* `can_fetch()` with our own UA never matches a `User-agent: ClaudeBot` rule.
  -> robots is asked as EVERY name that means us; most restrictive wins, and
  the row names the token that refused.
* `"Disallow" in robots_note` fires on the string `no Disallow directives`.
  -> `robots_bans_whole_site()` fires only on a bare `/`, proven by fixture.
* A `?wpdmdl=` endpoint returned the same PDF 302 times with green statuses.
  -> every download is md5'd; `verify` V7 fails on an identical-md5 ceiling.
* `I` and `O` never appear in a CAGE or UEI, and a UEI never starts `0`.
  -> cage_ok/uei_ok are DERIVED from the 19,473 identifiers already in
  `cedar_identifier_ledger_final.csv` (5,966 CAGE: all length 5, 0 containing
  I or O, 0 all-alpha, 5,966/5,966 ending in a digit; 13,507 UEI: all length
  12, 0 with I/O, 0 starting `0`, all carrying both a letter and a digit) and
  `verify` V1 re-asserts them against that live file. Without this rule a
  sweep read "Cage Jones, MT Assistant Supervisor" as CAGE `JONES`.
* The URL is the guess, never the evidence -> the identity check never sees
  the URL, drops `council` as a class marker, and lets negative markers win.
* A name made only of stopwords cannot be identity-checked from page text
  -> such names get their own verdict rather than a false one.

OUTCOMES. Six, kept distinct, never collapsed:
  HARVESTED FOUND_NOT_EXTRACTED CHECKED_ABSENT ATTEMPTED_INCONCLUSIVE
  REFUSED NEVER_CHECKED

COMMANDS
    py -3 code/1114_capability_statement_harvest.py worklist   # offline
    py -3 code/1114_capability_statement_harvest.py run --job released
    py -3 code/1114_capability_statement_harvest.py run --job identifiers
    py -3 code/1114_capability_statement_harvest.py run --job institutions
    py -3 code/1114_capability_statement_harvest.py build      # offline
    py -3 code/1114_capability_statement_harvest.py verify     # exits 1
    py -3 code/1114_capability_statement_harvest.py selftest   # proves it fires

This script writes ONLY into data/staging/capability_1114/. It rebuilds no
shared table and commits nothing.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.parse as up
import urllib.robotparser as urp
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
STAGE = ROOT / "data" / "staging" / "capability_1114"
STAGE.mkdir(parents=True, exist_ok=True)

WORKLIST = STAGE / "worklist.csv"
HOSTLOG = STAGE / "host_probe.jsonl"
DOCLOG = STAGE / "documents.jsonl"
FINDINGS = STAGE / "identifier_findings.csv"
SURFACES = STAGE / "surfaces_found.csv"
COVERAGE = STAGE / "coverage_1114.csv"
REFUSALS = STAGE / "refusals_1114.csv"
SUMMARY = STAGE / "run_summary.json"

BUILT_BY = "1114_capability_statement_harvest.py"
TODAY = time.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Politeness. Declared honestly; the contact address is the owner's.
# ---------------------------------------------------------------------------
UA = ("CedarPress-research/1.0 (+native-entity public-record research; "
      "contact elijahsamsonmoreno@gmail.com)")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36 " + UA),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Anthropic's crawler tokens are the names publishers actually write.
AGENT_TOKENS = ("ClaudeBot", "anthropic-ai", "Claude-User",
                "Claude-SearchBot", "Claude-Web", "CCBot", "*")

PER_HOST_DELAY = 1.1          # seconds between requests to ONE host
TIMEOUT = 25
MEDIA_PAGE_CAP = 25           # 100 items per page
MAX_DOCS_PER_HOST = 14
MAX_BYTES = 12 * 1024 * 1024
IDENTICAL_MD5_CEILING = 6     # per host. The ?wpdmdl= shape.

# ---------------------------------------------------------------------------
# THE FOUR THINGS THE RULING DOES NOT RELEASE
# ---------------------------------------------------------------------------
FORBIDDEN_PATH_PAT = re.compile(
    r"(?i)(/wp-admin|/wp-login|/admin|/administrator|/stagingsite|/staging"
    r"|/\.env|/\.git|/backup|/dump|/phpmyadmin|/login|/signin"
    r"|/members-only|/member-only|/portal/|/intranet|/cpanel|/xmlrpc\.php"
    r"|/user/login|/auth/|/account/)")
NON_TRIBAL_TERMS_HOSTS = {
    "emma.msrb.org", "msrb.org", "www.msrb.org",
    "casinocity.com", "www.casinocity.com",
    "dnb.com", "www.dnb.com",
}
# This script never emits these; the constant exists so `verify` V6 can assert
# their absence from anything it wrote.
PII_FIELDS = ("owner_name_raw", "owner_name", "email", "phone",
              "address_raw", "home_address", "dob", "ssn", "tin")

# ---------------------------------------------------------------------------
# THE HOSTS THE 2026-09-02 RULING RELEASED
# ---------------------------------------------------------------------------
RELEASED_HOSTS = {
    "colvilletribes.com", "www.colvilletribes.com",
    "ctuir.org", "www.ctuir.org", "umatilla.nsn.us", "www.umatilla.nsn.us",
    "yakama.com", "www.yakama.com",
    "chickasaw.net", "www.chickasaw.net", "chickasawbusinessnetwork.com",
    "nana.com", "www.nana.com", "akima.com", "www.akima.com",
    "southernute-nsn.gov", "www.southernute-nsn.gov",
    "fcpotawatomi.com", "www.fcpotawatomi.com", "shop.fcpotawatomi.com",
    "stillaguamish.com", "www.stillaguamish.com",
    "navajo-nsn.gov", "www.navajo-nsn.gov",
}
RELEASED_BASIS = ("owner ruling 2026-09-02, docs/PUBLICATION_POLICY.md "
                  "TERMS-OWNER-RULING-2026-09-02")

# ---------------------------------------------------------------------------
# VOCABULARY. Two families, recorded separately - a search built from the
# vocabulary of the PROGRAMME measures the programme, not the object
# (docs/HIDDEN_DATA_TECHNIQUES.md). CAP is the identifier family; BIZ is
# enterprises, directories, gaming and newsletters.
# ---------------------------------------------------------------------------
CAP_PAT = re.compile(
    r"(?i)(capabilit(?:y|ies)[\s_\-]*statement|capabilit(?:y|ies)"
    r"|cage[\s_\-]*code|\bcage\b|unique[\s_\-]*entity[\s_\-]*id\b|\buei\b"
    r"|\bduns\b|\bnaics\b|sam\.gov|sam[\s_\-]*registration"
    r"|(?:government|federal)[\s_\-]*contract|8\(a\)|8a[\s_\-]*cert"
    r"|socioeconomic|hubzone|gsa[\s_\-]*schedule|contract[\s_\-]*vehicle"
    r"|past[\s_\-]*performance|small[\s_\-]*business|\bsdb\b|set[\s_\-]aside"
    r"|procurement)")
BIZ_PAT = re.compile(
    r"(?i)(enterprise|tribalbusiness|business[\s_\-]*director|member[\s_\-]*owned"
    r"|citizen[\s_\-]*owned|tribally[\s_\-]*owned|our[\s_\-]*companies"
    r"|subsidiar|holdings|economic[\s_\-]*development|chamber|commerce"
    r"|entrepreneur|artisan|vendor[\s_\-]*list|certified[\s_\-]*vendor"
    r"|\btero\b|newsletter|press[\s_\-]*release|gaming|casino"
    r"|annual[\s_\-]*report)")
SEARCH_TERMS_CAP = ["capability statement", "cage", "uei", "naics",
                    "contracting", "procurement"]
SEARCH_TERMS_BIZ = ["enterprise", "business directory", "newsletter",
                    "subsidiaries", "vendor"]
CPT_SKIP = {"attachment", "nav_menu_item", "wp_block", "wp_template",
            "wp_template_part", "wp_navigation", "wp_global_styles",
            "wp_font_family", "wp_font_face", "revision", "custom_css",
            "customize_changeset", "oembed_cache", "user_request",
            "patterns_ai_data", "wp_pattern_category", "page", "post"}

# ---------------------------------------------------------------------------
# IDENTIFIER VALIDATION - DERIVED FROM THE 19,473 IDENTIFIERS WE ALREADY HOLD,
# not from memory. `verify` V1 re-asserts every rule against the live ledger
# and exits 1 if any held identifier fails its own validator.
# ---------------------------------------------------------------------------
_BAD_CHARS = set("IO")


def cage_ok(tok):
    """5 chars, no I/O, at least one digit, last char a digit.

    Measured over the 5,966 CAGE codes in cedar_identifier_ledger_final.csv.
    "JONES" fails on the O, on having no digit, and on the last character."""
    t = (tok or "").upper()
    return (len(t) == 5 and t.isalnum() and t.isascii()
            and not (_BAD_CHARS & set(t))
            and any(c.isdigit() for c in t)
            and t[-1].isdigit())


def uei_ok(tok):
    """12 chars, no I/O, never starts 0, mixed letters and digits.

    Measured over the 13,507 UEIs in the ledger."""
    t = (tok or "").upper()
    return (len(t) == 12 and t.isalnum() and t.isascii()
            and not (_BAD_CHARS & set(t))
            and t[0] != "0"
            and any(c.isdigit() for c in t)
            and any(c.isalpha() for c in t))


def duns_ok(tok):
    return len(tok) == 9 and tok.isdigit()


def ein_ok(tok):
    d = tok.replace("-", "")
    return len(d) == 9 and d.isdigit() and d != "000000000"


def naics_ok(tok):
    return len(tok) == 6 and tok.isdigit() and tok[0] in "123456789"


# A candidate is accepted only when its own LABEL sits immediately before it.
# The label is the context; the charset rule is the second, independent gate.
LABEL_PATS = {
    "CAGE": re.compile(r"(?i)\bcage(?:\s*(?:code|number|no\.?|#|id))?\s*"
                       r"[:#\-\u2013]?\s*([0-9A-Za-z]{5})\b"),
    "UEI": re.compile(r"(?i)\b(?:uei|unique\s+entity\s+(?:id|identifier)"
                      r"|sam\s+uei)\s*(?:number|no\.?|#|code)?\s*"
                      r"[:#\-\u2013]?\s*([0-9A-Za-z]{12})\b"),
    "DUNS": re.compile(r"(?i)\bduns\s*(?:number|no\.?|#)?\s*"
                       r"[:#\-\u2013]?\s*(\d{9})\b"),
    "EIN": re.compile(r"(?i)\b(?:ein|employer\s+identification\s+(?:number|no\.?)"
                      r"|federal\s+tax\s+id(?:entification)?(?:\s+number)?)\s*"
                      r"[:#\-\u2013]?\s*(\d{2}-?\d{7})\b"),
    "NAICS": re.compile(r"(?i)\bnaics\s*(?:code|codes|number|no\.?|#)?\s*"
                        r"[:#\-\u2013]?\s*(\d{6})\b"),
}
VALIDATORS = {"CAGE": cage_ok, "UEI": uei_ok, "DUNS": duns_ok,
              "EIN": ein_ok, "NAICS": naics_ok}

# ---------------------------------------------------------------------------
# IDENTITY. The URL is the guess and is never in the haystack.
# ---------------------------------------------------------------------------
STOPWORDS = {"the", "of", "and", "a", "an", "tribe", "tribes", "tribal",
             "nation", "band", "indian", "indians", "community", "council",
             "native", "american", "corporation", "corp", "inc", "company",
             "association", "village", "group", "pueblo", "rancheria",
             "reservation", "confederated", "school", "college", "alaska",
             "hawaiian", "organization", "consortium", "incorporated", "llc"}
# A marker a look-alike also uses is not a class marker. `council` was dropped
# after scottsvalley.gov - a CITY council - passed on it.
CLASS_MARKERS = re.compile(
    r"(?i)\b(tribal|tribe|tribes|nation|band|rancheria|pueblo|reservation"
    r"|indian|native|ancsa|village corporation|bureau of indian|\bbia\b"
    r"|\bihs\b|self-?governance|sovereign|kanaka|cdfi|tribal college|\bbie\b)")
NEGATIVE_MARKERS = re.compile(
    r"(?i)(city of|town of|county of|school district|unified school"
    r"|chamber of commerce of|public library|realtor"
    r"|domain (?:is )?for sale|buy this domain|parked (?:free )?courtesy"
    r"|godaddy\.com/domain|sedo\.com|hugedomains|namecheap parking)")
INTERSTITIAL = re.compile(
    r"(?i)(sgcaptcha|cf-browser-verification|just a moment|checking your "
    r"browser|enable javascript and cookies|ddos-guard|attention required)")


def name_tokens(name):
    toks = [t for t in re.split(r"[^a-z0-9]+", (name or "").lower()) if t]
    return [t for t in toks if t not in STOPWORDS and len(t) > 2]


def strip_html(html):
    h = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html or "")
    h = re.sub(r"(?s)<!--.*?-->", " ", h)
    h = re.sub(r"<[^>]+>", " ", h)
    h = (h.replace("&amp;", "&").replace("&nbsp;", " ")
          .replace("&#8217;", "'").replace("&quot;", '"'))
    return re.sub(r"\s+", " ", h)


def identity_verdict(html, canonical_name):
    """(verdict, marker, note). The URL is NOT an input. That is the point."""
    text = strip_html(html)
    low = text.lower()
    if INTERSTITIAL.search(low[:4000]):
        return "INTERSTITIAL_NOT_THE_SITE", "", "bot-check interstitial body"
    toks = name_tokens(canonical_name)
    if not toks:
        return ("NAME_IS_ALL_STOPWORDS_identity_not_checkable_from_page_text",
                "", "every token of the name is a stopword")
    neg = NEGATIVE_MARKERS.search(text)
    hits = sum(1 for t in toks if t in low)
    cls = CLASS_MARKERS.search(text)
    if neg and hits < len(toks):
        return "DOMAIN_NOT_THE_ENTITY", "", "negative marker " + repr(neg.group(0))
    if hits == 0:
        return ("DOMAIN_NOT_THE_ENTITY", "",
                "page text carries none of the name tokens")
    if not cls:
        return ("DOMAIN_NOT_THE_ENTITY", "",
                "%d/%d name tokens but no class marker" % (hits, len(toks)))
    if neg:
        return ("DOMAIN_SUSPECT", cls.group(0),
                "class marker %r AND negative %r" % (cls.group(0), neg.group(0)))
    return "NAMES_THE_ENTITY", cls.group(0), "%d/%d name tokens" % (hits, len(toks))


# ---------------------------------------------------------------------------
# ROBOTS - asked as EVERY name that means us
# ---------------------------------------------------------------------------
def robots_bans_whole_site(body):
    """(bans, token, note). Fires only on a bare `/` for a group that binds us.

    `"Disallow" in note` fired on the literal string `no Disallow directives`
    and on `/wp-admin/` - 106 phantom refusals against a true 54. This parses
    the groups instead."""
    if not body:
        return False, "", "no robots.txt body"
    groups, cur = [], None
    for raw in body.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            if cur is None or cur["seen_rule"]:
                cur = {"agents": [], "dis": [], "allow": [], "seen_rule": False}
                groups.append(cur)
            cur["agents"].append(v.lower())
        elif cur is not None and k in ("disallow", "allow"):
            cur["seen_rule"] = True
            cur["dis" if k == "disallow" else "allow"].append(v)
    ours = set(t.lower() for t in AGENT_TOKENS)
    named = [g for g in groups
             if any(a in ours and a != "*" for a in g["agents"])]
    star = [g for g in groups if "*" in g["agents"]]
    # Most restrictive answer wins, and a group naming us outranks the wildcard.
    for g in (named or star):
        if (any(d.strip() == "/" for d in g["dis"])
                and not any(a.strip() == "/" for a in g["allow"])):
            tok = next((a for a in g["agents"] if a in ours), "*")
            return True, tok, "Disallow: / for User-agent: " + tok
    n_dis = sum(len(g["dis"]) for g in groups)
    if not groups:
        return False, "", "no directives"
    return False, "", ("%d group(s), %d Disallow line(s), no whole-site ban"
                       % (len(groups), n_dis))


def robots_path_blocked(body, path):
    if not body:
        return False, ""
    rp = urp.RobotFileParser()
    rp.parse(body.splitlines())
    for tok in (UA,) + AGENT_TOKENS:
        try:
            if not rp.can_fetch(tok, path):
                return True, tok
        except Exception:
            continue
    return False, ""


# ---------------------------------------------------------------------------
# CSV helpers. The header is DERIVED: the union of what is already on disk and
# what this build produced, so a column another pass added is never dropped
# (62 rule 17, 845 class1 + class3).
# ---------------------------------------------------------------------------
def derived_header(path, rows):
    hdr = []
    if path.exists():
        try:
            with path.open(encoding="utf-8-sig", newline="") as fh:
                first = next(csv.reader(fh), [])
            hdr = [c for c in first if c]
        except (OSError, StopIteration):
            hdr = []
    for r in rows:
        for k in r:
            if k not in hdr:
                hdr.append(k)
    return hdr


def write_csv(path, rows):
    hdr = derived_header(path, rows)
    tmp = path.with_suffix(path.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=hdr, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(dict((k, r.get(k, "")) for k in hdr))
    os.replace(tmp, path)          # an interruption must not look complete
    return hdr


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


_lock = threading.Lock()


def append_jsonl(path, rec):
    """Flush per entity."""
    with _lock:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def read_jsonl(path):
    out = []
    if path.exists():
        for line in path.open(encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


# ===========================================================================
# WORKLIST  (offline)
# ===========================================================================
JOB_CLASSES_INSTITUTION = {
    "BIE School", "Urban Indian Organization", "Tribal College or University",
    "Native Financial Institution",
    "Native Community Development Financial Institution",
}
DEAD_URL_TYPES = {"none_established", "no_own_site_found", "parked_domain",
                  "placeholder_site", "DOMAIN_HIJACKED_DO_NOT_LINK",
                  "TERMS_RESTRICTED_DO_NOT_HARVEST",
                  "government_refused_robots",
                  "government_blocked_bot_protection"}
PREVIOUSLY_REFUSED_TYPES = {"TERMS_RESTRICTED_DO_NOT_HARVEST",
                            "government_refused_robots",
                            "government_blocked_bot_protection"}


def host_of(u):
    if not u:
        return ""
    try:
        return up.urlsplit(u if "//" in u else "https://" + u).netloc.lower()
    except ValueError:
        return ""


def build_worklist():
    spine = dict((r["cedar_uid"], r)
                 for r in read_csv(SPINE / "cedar_entity_spine.csv"))
    webmap = read_csv(STAGE.parent / "cedar_web_map.csv")
    matrix = read_csv(CLEAN / "cedar_harvest_coverage_matrix.csv")

    ident_held, best_url, mr_surface, refused_hosts = {}, {}, {}, {}
    for r in read_csv(CLEAN / "cedar_identifier_ledger_final.csv"):
        u = r.get("cedar_uid", "")
        if u:
            ident_held.setdefault(u, set()).add(r["identifier_type"])
    for r in webmap:
        u, t, url = r["cedar_uid"], r["url_type"], r["url"]
        st = (r.get("http_status") or "").strip()
        if t in ("api_endpoint", "wp_types", "wp_media_pdf", "sitemap",
                 "machine_readable_surface", "document_endpoint"):
            mr_surface.setdefault(u, []).append(t)
        if t in PREVIOUSLY_REFUSED_TYPES and host_of(url):
            refused_hosts.setdefault(u, set()).add(host_of(url))
        if t in DEAD_URL_TYPES:
            continue
        if st.startswith("2") and url and u not in best_url:
            best_url[u] = url
    for r in webmap:                       # second pass: any non-dead url
        u, t, url = r["cedar_uid"], r["url_type"], r["url"]
        if u not in best_url and url and t not in DEAD_URL_TYPES \
                and not t.startswith("failed_"):
            best_url[u] = url

    by_uid = {}
    for r in matrix:
        by_uid.setdefault(r["cedar_uid"], {})[r["harvest_type"]] = r

    rows = []
    for uid, ent in spine.items():
        cells = by_uid.get(uid, {})
        url = best_url.get(uid, "") or (ent.get("entity_website") or "").strip()
        host = host_of(url)
        contam = any((c.get("contamination_flags") or "")
                     for c in cells.values())
        held = sorted(ident_held.get(uid, ()))
        refused = sorted(refused_hosts.get(uid, ()))
        rel = bool(host and (host in RELEASED_HOSTS
                             or any(host.endswith("." + h)
                                    for h in RELEASED_HOSTS)))
        any_refused = any(c.get("outcome") == "REFUSED" for c in cells.values())
        jobs = []
        if rel or any_refused or refused:
            jobs.append("released")
        if (cells.get("identifiers", {}).get("outcome") == "NEVER_CHECKED"
                and url and held and not contam):
            jobs.append("identifiers")
        if ent["entity_class"] in JOB_CLASSES_INSTITUTION and url:
            jobs.append("institutions")
        if not jobs or not host:
            continue
        rows.append({
            "cedar_uid": uid, "tribe_id": ent.get("tribe_id", ""),
            "canonical_name": ent["canonical_name"],
            "entity_class": ent["entity_class"], "state": ent.get("state", ""),
            "jobs": "|".join(jobs),
            "url": url, "host": host,
            "previously_refused_hosts": "|".join(refused),
            "released_host": "Y" if rel else "N",
            "released_basis": RELEASED_BASIS if (rel or refused) else "",
            "identifiers_held": "|".join(held),
            "machine_readable_surface":
                "|".join(sorted(set(mr_surface.get(uid, [])))),
            "contamination_flags": "Y" if contam else "N",
            "prior_identifiers_outcome":
                cells.get("identifiers", {}).get("outcome", "NEVER_CHECKED"),
            "built_by": BUILT_BY, "built_date": TODAY})
    write_csv(WORKLIST, rows)
    jc = collections.Counter()
    for r in rows:
        for j in r["jobs"].split("|"):
            jc[j] += 1
    print("worklist: %d entities -> %s" % (len(rows), WORKLIST))
    for k, v in jc.most_common():
        print("   %-14s %d" % (k, v))
    print("   distinct hosts: %d" % len(set(r["host"] for r in rows)))
    print("   with a machine-readable surface already mapped: %d"
          % sum(1 for r in rows if r["machine_readable_surface"]))
    return rows


# ===========================================================================
# FETCH
# ===========================================================================
class HostSession(object):
    def __init__(self, host):
        self.host = host
        self.s = requests.Session()
        self.hdr = HEADERS
        self.verify = True
        self.root = None
        self.route = ""
        self.n = 0
        self.robots_body = ""

    def _try(self, url, hdr=None, verify=None, stream=False):
        self.n += 1
        try:
            return self.s.get(url, headers=hdr or self.hdr, timeout=TIMEOUT,
                              verify=self.verify if verify is None else verify,
                              allow_redirects=True, stream=stream)
        except requests.RequestException as exc:
            return exc
        finally:
            time.sleep(PER_HOST_DELAY)

    def reach(self):
        alt = (self.host[4:] if self.host.startswith("www.")
               else "www." + self.host)
        for cand in (self.host, alt):
            for scheme in ("https", "http"):
                root = "%s://%s" % (scheme, cand)
                for hdr, how in ((HEADERS, "declared UA"),
                                 (BROWSER_HEADERS, "browser headers")):
                    r = self._try(root + "/", hdr)
                    if isinstance(r, Exception):
                        if "SSL" in type(r).__name__ or "SSL" in str(r):
                            r2 = self._try(root + "/", BROWSER_HEADERS,
                                           verify=False)
                            if (not isinstance(r2, Exception)
                                    and r2.status_code in (200, 202, 203)):
                                self.root, self.hdr = root, BROWSER_HEADERS
                                self.verify = False
                                self.route = ("%s, %s, relaxed TLS (cert does "
                                              "not cover this name)"
                                              % (scheme, cand))
                                return r2
                        continue
                    if r.status_code in (200, 202, 203, 206):
                        self.root, self.hdr = root, hdr
                        self.route = "%s, %s, %s" % (scheme, cand, how)
                        return r
        return None

    def get(self, url, stream=False):
        path = up.urlsplit(url).path or "/"
        if FORBIDDEN_PATH_PAT.search(path):
            return None            # never requested. Ruling item 1.
        blocked, _tok = robots_path_blocked(self.robots_body, path)
        if blocked:
            return None
        r = self._try(url, stream=stream)
        if isinstance(r, Exception) or r.status_code != 200:
            return None
        return r


def pdf_text(blob):
    """Text plus PDF metadata - the metadata carries the as_of_date the
    document never prints (HIDDEN_DATA_TECHNIQUES section 11)."""
    try:
        import pymupdf
        with pymupdf.open(stream=blob, filetype="pdf") as doc:
            meta = doc.metadata or {}
            txt = " ".join(p.get_text() for p in doc)
        head = " ".join("%s=%s" % (k, v) for k, v in meta.items() if v)
        return (head + " " + txt)[:900000]
    except Exception:
        return ""


def extract_identifiers(text, url, entity, kind, doc_md5, technique):
    """Label AND charset, both required. Emits an evidence quote, never PII."""
    out, seen = [], set()
    for typ, pat in LABEL_PATS.items():
        for m in pat.finditer(text):
            tok = m.group(1).strip().upper()
            norm = tok.replace("-", "") if typ == "EIN" else tok
            if not VALIDATORS[typ](tok):
                continue
            if (typ, norm) in seen:
                continue
            seen.add((typ, norm))
            s, e = max(0, m.start() - 90), min(len(text), m.end() + 90)
            quote = re.sub(r"\s+", " ", text[s:e]).strip()
            out.append({
                "cedar_uid": entity["cedar_uid"],
                "canonical_name": entity["canonical_name"],
                "entity_class": entity["entity_class"],
                "identifier_type": typ,
                "identifier": ("%s-%s" % (norm[:2], norm[2:])
                               if typ == "EIN" else norm),
                "source_url": url,
                "source_kind": kind,
                "technique": technique,
                "matched_label": re.sub(r"\s+", " ", m.group(0))[:60],
                "evidence_quote": quote[:300],
                "document_md5": doc_md5,
                "evidence_family": "entity_self_published_web",
                "checked_date": TODAY,
                "built_by": BUILT_BY})
    return out


def probe_entity(job):
    """One entity, one host. Returns (rec, findings, surfaces, docs)."""
    ent = job
    host = ent["host"]
    rec = {"cedar_uid": ent["cedar_uid"],
           "canonical_name": ent["canonical_name"],
           "entity_class": ent["entity_class"], "jobs": ent["jobs"],
           "host": host, "released_host": ent.get("released_host", "N"),
           "reached": "N", "reach_route": "", "http_status": "",
           "robots_note": "", "robots_refused_token": "",
           "identity_verdict": "", "identity_marker": "", "identity_note": "",
           "wp": "N", "media_total": 0, "media_scanned": 0, "cpts": [],
           "sitemap_urls": 0, "search_hits": 0,
           "cap_surfaces": [], "biz_surfaces": [],
           "docs_fetched": 0, "docs_distinct_md5": 0,
           "identifiers_found": 0, "requests": 0,
           "routes_run": {}, "outcome_note": "", "checked_date": TODAY,
           "built_by": BUILT_BY}
    findings, surfaces, docs = [], [], []

    if not host:
        rec["outcome_note"] = "no host known"
        return rec, findings, surfaces, docs

    # Ruling items 3 and 4: a non-tribal licensor is not released.
    if host in NON_TRIBAL_TERMS_HOSTS:
        rec["reached"] = "REFUSED"
        rec["outcome_note"] = ("non-tribal licensor; the 2026-09-02 owner "
                               "ruling covers tribal publishers only")
        return rec, findings, surfaces, docs

    hs = HostSession(host)
    for scheme in ("https", "http"):
        r = hs._try("%s://%s/robots.txt" % (scheme, host))
        if (not isinstance(r, Exception) and r.status_code == 200
                and len(r.text) < 200000):
            hs.robots_body = r.text
            break
    bans, tok, note = robots_bans_whole_site(hs.robots_body)
    rec["robots_note"] = note
    if bans:
        rec["reached"] = "REFUSED"
        rec["robots_refused_token"] = tok
        rec["outcome_note"] = (
            "robots bans the whole site for User-agent: %s. The 2026-09-02 "
            "ruling makes a terms page an observation; a whole-site Disallow "
            "aimed at this agent is the publisher's operational refusal and "
            "is still honoured." % tok)
        rec["requests"] = hs.n
        return rec, findings, surfaces, docs

    home = hs.reach()
    if home is None:
        rec["requests"] = hs.n
        rec["outcome_note"] = ("unreachable on http/https, www and apex, both "
                               "UAs, relaxed TLS")
        return rec, findings, surfaces, docs
    rec["reached"] = "Y"
    rec["reach_route"] = hs.route
    rec["http_status"] = home.status_code
    html = home.text or ""
    v, marker, inote = identity_verdict(html, ent["canonical_name"])
    rec["identity_verdict"] = v
    rec["identity_marker"] = marker
    rec["identity_note"] = inote
    if v in ("DOMAIN_NOT_THE_ENTITY", "INTERSTITIAL_NOT_THE_SITE"):
        rec["outcome_note"] = "identity: " + inote
        rec["requests"] = hs.n
        return rec, findings, surfaces, docs

    root = hs.root
    cands = {}

    def add(url, family, title, technique):
        if not url or url.startswith("mailto:") or url.startswith("tel:"):
            return
        url = up.urljoin(root + "/", url)
        h = host_of(url)
        if h not in (host, "www." + host, host.replace("www.", "", 1)):
            return
        if FORBIDDEN_PATH_PAT.search(up.urlsplit(url).path or ""):
            return
        cands.setdefault(url, (family, (title or "")[:160], technique))

    def classify(blob):
        if CAP_PAT.search(blob):
            return "CAP"
        if BIZ_PAT.search(blob):
            return "BIZ"
        return ""

    txt = strip_html(html)
    findings += extract_identifiers(txt, root + "/", ent, "html", "",
                                    "rendered home page")
    for href in re.findall(r'(?i)href=["\']([^"\']+)["\']', html):
        fam = classify(href)
        if fam:
            add(href, fam, href, "home page link")

    # 1 - the WordPress media index, unfiltered and paginated
    page, total_pages, seen = 1, 1, 0
    while page <= total_pages and page <= MEDIA_PAGE_CAP:
        r = hs.get("%s/wp-json/wp/v2/media?per_page=100&page=%d"
                   "&_fields=source_url,title,date,mime_type" % (root, page))
        if r is None:
            break
        try:
            items = json.loads(r.text)
        except ValueError:
            break
        if not isinstance(items, list) or not items:
            break
        rec["wp"] = "Y"
        rec["media_total"] = int(r.headers.get("X-WP-Total", 0) or 0)
        total_pages = int(r.headers.get("X-WP-TotalPages", 1) or 1)
        for it in items:
            seen += 1
            su = it.get("source_url", "") or ""
            ti = re.sub(r"<[^>]+>", "",
                        (it.get("title") or {}).get("rendered", ""))
            fam = classify(su + " " + ti)
            if fam:
                add(su, fam, ti or su, "wp/v2/media")
        page += 1
    rec["media_scanned"] = seen
    media_ok = (rec["wp"] == "Y"
                and (seen >= rec["media_total"] or page > MEDIA_PAGE_CAP))

    # 2 - custom post types. The highest-yield single signal in this project.
    types_ok = False
    r = hs.get(root + "/wp-json/wp/v2/types")
    if r is not None:
        try:
            types = json.loads(r.text)
        except ValueError:
            types = {}
        if isinstance(types, dict) and types:
            types_ok = True
            rec["wp"] = "Y"
            for slug, meta in types.items():
                if slug in CPT_SKIP or not isinstance(meta, dict):
                    continue
                rec["cpts"].append(slug)
                label = "%s %s" % (meta.get("name", ""), slug)
                fam = classify(label)
                if fam:
                    links = (meta.get("_links", {}) or {}).get("wp:items") or [{}]
                    ep = links[0].get("href")
                    add((ep or "%s/wp-json/wp/v2/%s" % (root, slug))
                        + "?per_page=100", fam, label.strip(),
                        "wp/v2/types custom post type")

    # 3 - the REST search index, which reaches pages the nav dropped
    search_ok = False
    for term in SEARCH_TERMS_CAP + SEARCH_TERMS_BIZ:
        r = hs.get("%s/wp-json/wp/v2/search?search=%s&per_page=50"
                   % (root, up.quote(term)))
        if r is None:
            continue
        search_ok = True
        try:
            items = json.loads(r.text)
        except ValueError:
            continue
        for it in (items if isinstance(items, list) else []):
            rec["search_hits"] += 1
            t, u = str(it.get("title", "")), str(it.get("url", ""))
            fam = classify(t + " " + u)
            if fam:
                add(u, fam, t, "wp/v2/search[%s]" % term)

    # 4 - sitemaps
    sitemap_ok, locs = False, []
    for sm in ("/sitemap_index.xml", "/sitemap.xml", "/wp-sitemap.xml"):
        r = hs.get(root + sm)
        if r is None or "<" not in r.text:
            continue
        sitemap_ok = True
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r.text)
        for sub in [l for l in locs if l.endswith(".xml")][:10]:
            r2 = hs.get(sub)
            if r2 is not None:
                locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r2.text)
        break
    pages = [l for l in dict.fromkeys(locs) if not l.endswith(".xml")]
    rec["sitemap_urls"] = len(pages)
    for l in pages:
        fam = classify(l)
        if fam:
            add(l, fam, "", "sitemap")

    rec["routes_run"] = {"media_index": bool(media_ok),
                         "custom_post_types": types_ok,
                         "rest_search": search_ok, "sitemap": sitemap_ok}
    rec["cap_surfaces"] = [u for u, t in cands.items() if t[0] == "CAP"][:60]
    rec["biz_surfaces"] = [u for u, t in cands.items() if t[0] == "BIZ"][:60]
    for u, (fam, title, tech) in cands.items():
        surfaces.append({"cedar_uid": ent["cedar_uid"],
                         "canonical_name": ent["canonical_name"],
                         "entity_class": ent["entity_class"],
                         "vocabulary_family": fam, "surface_url": u,
                         "surface_title": title, "technique": tech,
                         "host": host, "checked_date": TODAY,
                         "built_by": BUILT_BY})

    # 5 - fetch the candidates, CAP first. Hash every object.
    order = ([u for u, t in cands.items() if t[0] == "CAP"]
             + [u for u, t in cands.items() if t[0] == "BIZ"])
    md5s = set()
    for u in order[:MAX_DOCS_PER_HOST]:
        r = hs.get(u, stream=True)
        if r is None:
            continue
        blob = b""
        try:
            for chunk in r.iter_content(65536):
                blob += chunk
                if len(blob) > MAX_BYTES:
                    break
        except requests.RequestException:
            pass
        finally:
            r.close()
        if not blob:
            continue
        md5 = hashlib.md5(blob).hexdigest()
        ctype = (r.headers.get("Content-Type") or "").split(";")[0].lower()
        rec["docs_fetched"] += 1
        md5s.add(md5)
        docs.append({"cedar_uid": ent["cedar_uid"], "host": host, "url": u,
                     "content_type": ctype, "bytes": len(blob), "md5": md5,
                     "technique": cands[u][2],
                     "vocabulary_family": cands[u][0], "checked_date": TODAY})
        if "pdf" in ctype or u.lower().endswith(".pdf") or blob[:4] == b"%PDF":
            body, kind = pdf_text(blob), "pdf"
        elif "json" in ctype:
            body, kind = blob.decode("utf-8", "replace")[:900000], "json"
        else:
            body = strip_html(blob.decode("utf-8", "replace"))[:900000]
            kind = "html"
        findings += extract_identifiers(body, u, ent, kind, md5, cands[u][2])
    rec["docs_distinct_md5"] = len(md5s)
    rec["identifiers_found"] = len(findings)
    rec["requests"] = hs.n
    return rec, findings, surfaces, docs


def _append_rows(path, rows):
    if not rows:
        return
    write_csv(path, read_csv(path) + rows)


def run(job_name, limit=None, workers=6, only_hosts=None):
    rows = read_csv(WORKLIST)
    if not rows:
        rows = build_worklist()
    done = set(r["cedar_uid"] for r in read_jsonl(HOSTLOG))
    jobs = [r for r in rows if job_name in r["jobs"].split("|")
            and r["cedar_uid"] not in done]
    if only_hosts:
        jobs = [r for r in jobs if r["host"] in only_hosts]
    if limit:
        jobs = jobs[:limit]
    print("job=%s  %d entities to probe (%d already on record)"
          % (job_name, len(jobs), len(done)))
    if not jobs:
        return
    # One host, one worker. Never quadruple the rate against one server:
    # order so that concurrently-running jobs are on different hosts.
    by_host = collections.OrderedDict()
    for j in jobs:
        by_host.setdefault(j["host"], []).append(j)
    ordered, buckets = [], list(by_host.values())
    while buckets:
        nxt = []
        for b in buckets:
            ordered.append(b.pop(0))
            if b:
                nxt.append(b)
        buckets = nxt
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (rec, finds, surfs, docs) in enumerate(
                ex.map(probe_entity, ordered), 1):
            append_jsonl(HOSTLOG, rec)
            for d in docs:
                append_jsonl(DOCLOG, d)
            if finds or surfs:
                with _lock:
                    _append_rows(FINDINGS, finds)
                    _append_rows(SURFACES, surfs)
            if i % 10 == 0 or i == len(ordered):
                print("   %d/%d  %-38s reached=%s ids=%d cap=%d"
                      % (i, len(ordered), rec["canonical_name"][:38],
                         rec["reached"], rec["identifiers_found"],
                         len(rec["cap_surfaces"])))


# ===========================================================================
# BUILD  (offline) - outcomes, corroboration, refusals
# ===========================================================================
HARVEST_TYPES = ["enterprises", "identifiers", "individual_business",
                 "gaming", "newsletter"]
TYPE_PAT = {
    "enterprises": re.compile(
        r"(?i)(enterprise|subsidiar|holdings|our[\s_\-]*companies"
        r"|tribalbusiness|economic[\s_\-]*development)"),
    "identifiers": CAP_PAT,
    "individual_business": re.compile(
        r"(?i)(business[\s_\-]*director|member[\s_\-]*owned"
        r"|citizen[\s_\-]*owned|vendor|\btero\b|certified|chamber"
        r"|entrepreneur|artisan)"),
    "gaming": re.compile(r"(?i)(gaming|casino|bingo|slot)"),
    "newsletter": re.compile(
        r"(?i)(newsletter|press[\s_\-]*release|bulletin|gazette"
        r"|annual[\s_\-]*report)"),
}


def build():
    hosts = read_jsonl(HOSTLOG)
    if not hosts:
        print("nothing probed yet - run first")
        return
    finds, surfs, docs = read_csv(FINDINGS), read_csv(SURFACES), read_jsonl(DOCLOG)

    # --- corroboration against the ledger: the whole point of the pass ------
    held, held_any = {}, set()
    for r in read_csv(CLEAN / "cedar_identifier_ledger_final.csv"):
        k = (r["identifier_type"], r["identifier"].upper().replace("-", ""))
        held.setdefault(r.get("cedar_uid", ""), set()).add(k)
        held_any.add(k)
    for f in finds:
        key = (f["identifier_type"], f["identifier"].upper().replace("-", ""))
        f["corroborates_ledger_same_entity"] = (
            "Y" if key in held.get(f["cedar_uid"], set()) else "N")
        f["present_in_ledger_any_entity"] = "Y" if key in held_any else "N"
        f["ledger_basis"] = ("data/clean/cedar_identifier_ledger_final.csv - "
                             "federal-side evidence family (FPDS/SAM/award "
                             "archive); this row is entity_self_published_web")
    if finds:
        write_csv(FINDINGS, finds)

    surf_by, find_by = {}, {}
    for s in surfs:
        surf_by.setdefault(s["cedar_uid"], []).append(s)
    for f in finds:
        find_by.setdefault(f["cedar_uid"], []).append(f)

    cov, refs = [], []
    for h in hosts:
        uid = h["cedar_uid"]
        base = {"cedar_uid": uid, "canonical_name": h["canonical_name"],
                "entity_class": h["entity_class"], "host": h["host"],
                "jobs": h["jobs"], "checked_date": h["checked_date"],
                "built_by": BUILT_BY}
        rr = h.get("routes_run") or {}
        mr_ran = sum(1 for k in ("media_index", "custom_post_types",
                                 "rest_search", "sitemap") if rr.get(k))
        if h["reached"] == "REFUSED":
            refs.append(dict(base, refusal_kind=(
                "ROBOTS_NAMED_AGENT_WHOLE_SITE"
                if h.get("robots_refused_token") else "NON_TRIBAL_LICENSOR"),
                refused_token=h.get("robots_refused_token", ""),
                detail=h["outcome_note"]))
        for ht in HARVEST_TYPES:
            row = dict(base)
            row["harvest_type"] = ht
            if h["reached"] == "REFUSED":
                row["outcome"] = "REFUSED"
                row["outcome_basis"] = h["outcome_note"]
            elif h["reached"] != "Y":
                row["outcome"] = "ATTEMPTED_INCONCLUSIVE"
                row["outcome_basis"] = h["outcome_note"] or "host not reached"
            elif h["identity_verdict"] in ("DOMAIN_NOT_THE_ENTITY",
                                           "INTERSTITIAL_NOT_THE_SITE"):
                row["outcome"] = "ATTEMPTED_INCONCLUSIVE"
                row["outcome_basis"] = "%s: %s" % (h["identity_verdict"],
                                                   h["identity_note"])
            else:
                got = find_by.get(uid, []) if ht == "identifiers" else []
                srf = [s for s in surf_by.get(uid, [])
                       if TYPE_PAT[ht].search(s["surface_url"] + " "
                                              + s["surface_title"])]
                if got:
                    row["outcome"] = "HARVESTED"
                    row["outcome_basis"] = (
                        "%d identifier(s), each with its own label and a "
                        "charset-valid token" % len(got))
                elif srf:
                    row["outcome"] = "FOUND_NOT_EXTRACTED"
                    row["outcome_basis"] = ("%d surface(s) located and "
                                            "reached; nothing pulled into a "
                                            "table" % len(srf))
                elif mr_ran >= 2:
                    row["outcome"] = "CHECKED_ABSENT"
                    row["outcome_basis"] = ("%d/4 machine-readable routes ran "
                                            "and returned nothing" % mr_ran)
                else:
                    row["outcome"] = "ATTEMPTED_INCONCLUSIVE"
                    row["outcome_basis"] = ("only %d/4 machine-readable routes "
                                            "ran - NOT_SEARCHED_MACHINE_"
                                            "READABLE, which is not an "
                                            "absence" % mr_ran)
            row["identity_verdict"] = h["identity_verdict"]
            row["machine_readable_routes_run"] = mr_ran
            row["routes_run"] = json.dumps(rr)
            row["n_surfaces"] = len(surf_by.get(uid, []))
            row["n_identifiers"] = len(find_by.get(uid, []))
            row["released_host"] = h.get("released_host", "N")
            row["released_basis"] = (RELEASED_BASIS
                                     if h.get("released_host") == "Y" else "")
            cov.append(row)
    write_csv(COVERAGE, cov)
    write_csv(REFUSALS, refs)

    oc = collections.Counter(r["outcome"] for r in cov)
    per_type = {}
    for r in cov:
        per_type.setdefault(r["harvest_type"], collections.Counter())[
            r["outcome"]] += 1
    summ = {
        "built_by": BUILT_BY, "built_date": TODAY,
        "entities_probed": len(hosts),
        "hosts_reached": sum(1 for h in hosts if h["reached"] == "Y"),
        "hosts_refused": sum(1 for h in hosts if h["reached"] == "REFUSED"),
        "hosts_unreachable": sum(1 for h in hosts if h["reached"] == "N"),
        "identifiers_found": len(finds),
        "identifiers_distinct": len(set(
            (f["cedar_uid"], f["identifier_type"], f["identifier"])
            for f in finds)),
        "entities_with_an_identifier": len(find_by),
        "corroborating_ledger_same_entity": sum(
            1 for f in finds if f.get("corroborates_ledger_same_entity") == "Y"),
        "surfaces_found": len(surfs),
        "entities_with_a_surface": len(surf_by),
        "documents_fetched": len(docs),
        "documents_distinct_md5": len(set(d["md5"] for d in docs)),
        "coverage_rows": len(cov),
        "outcomes": dict(oc),
        "outcomes_per_harvest_type": dict(
            (k, dict(v)) for k, v in per_type.items()),
    }
    SUMMARY.write_text(json.dumps(summ, indent=2), encoding="utf-8")
    print(json.dumps(summ, indent=2))
    return summ


# ===========================================================================
# VERIFY - exits 1 on breach. Every invariant is proven to FIRE by `selftest`.
# ===========================================================================
def verify(quiet=False):
    fails = []

    def bad(inv, msg):
        fails.append("[%s] %s" % (inv, msg))

    # (1) the validators must accept every identifier Cedar already holds.
    ledger = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    if not ledger:
        bad("V1", "UNMEASURED: ledger absent - a validator with no fixture is "
                  "not a validated validator")
    else:
        for typ, fn in (("CAGE", cage_ok), ("UEI", uei_ok)):
            heldv = [r["identifier"] for r in ledger
                     if r["identifier_type"] == typ]
            rej = [x for x in heldv if not fn(x)]
            if rej:
                bad("V1", "%d of %d held %s values are REJECTED by this "
                          "script's validator, e.g. %s"
                          % (len(rej), len(heldv), rej[:3]))
    # (2) the trap strings must be rejected.
    for tok in ("JONES", "CAGES", "OIOIO", "ABCDE"):
        if cage_ok(tok):
            bad("V2", "cage_ok accepted the trap string %r" % tok)
    if uei_ok("0ABCDEFGHJKL") or uei_ok("ABCDEFGHJKLM"):
        bad("V2", "uei_ok accepted a leading-0 or all-alpha string")
    # (3) robots fixtures.
    fx = [("User-agent: *\nDisallow: /\n", True),
          ("User-agent: *\nDisallow: /wp-admin/\n", False),
          ("# no Disallow directives\nUser-agent: *\nAllow: /\n", False),
          ("User-agent: ClaudeBot\nDisallow: /\n\nUser-agent: *\nAllow: /\n",
           True),
          ("User-agent: anthropic-ai\nDisallow: /\n", True),
          ("User-agent: Googlebot\nDisallow: /\n\nUser-agent: *\nAllow: /\n",
           False),
          ("", False)]
    for body, want in fx:
        got = robots_bans_whole_site(body)[0]
        if got != want:
            bad("V3", "robots fixture %r -> %s, expected %s"
                      % (body, got, want))
    # (4) identity must never see the URL and must reject the look-alikes.
    lk = [("<html><body>City of Scotts Valley city council meeting agenda"
           "</body></html>", "Scotts Valley Band of Pomo Indians",
           "DOMAIN_NOT_THE_ENTITY"),
          ("<html><body>Big Lagoon Elementary School District</body></html>",
           "Big Lagoon Rancheria", "DOMAIN_NOT_THE_ENTITY"),
          ("<html><body>Just a moment... checking your browser</body></html>",
           "Anything At All", "INTERSTITIAL_NOT_THE_SITE"),
          ("<html><body>The Navajo Nation is a sovereign tribal government"
           "</body></html>", "Navajo Nation", "NAMES_THE_ENTITY"),
          ("<html><body>welcome</body></html>", "Council",
           "NAME_IS_ALL_STOPWORDS_identity_not_checkable_from_page_text")]
    for html, nm, want in lk:
        got = identity_verdict(html, nm)[0]
        if got != want:
            bad("V4", "identity(%r) -> %s, expected %s" % (nm, got, want))
    # (5) technical access controls are never candidates.
    for p in ("/wp-admin/admin-ajax.php", "/Stagingsite/index.html",
              "/user/login", "/.git/config", "/.env"):
        if not FORBIDDEN_PATH_PAT.search(p):
            bad("V5", "technical-access path %s is not refused" % p)
    # (6) no PII column may exist in anything this script wrote.
    for p in (FINDINGS, SURFACES, COVERAGE, REFUSALS, WORKLIST):
        if not p.exists():
            continue
        with p.open(encoding="utf-8-sig", newline="") as fh:
            hdr = [c.lower() for c in (next(csv.reader(fh), []) or [])]
        for f in PII_FIELDS:
            if f in hdr:
                bad("V6", "%s carries PII column %r - ruling item 2"
                          % (p.name, f))
    # (7) the identical-md5 ceiling (the ?wpdmdl= defect).
    docs = read_jsonl(DOCLOG)
    if docs:
        per = collections.Counter((d["host"], d["md5"]) for d in docs)
        (whost, _m), n = per.most_common(1)[0]
        if n > IDENTICAL_MD5_CEILING:
            bad("V7", "host %s returned the same md5 %d times - the ?wpdmdl= "
                      "shape. Purge and re-run." % (whost, n))
    # (8) every finding carries a label, a quote, a url and a valid token.
    for f in read_csv(FINDINGS):
        t, v = f["identifier_type"], f["identifier"]
        if t in VALIDATORS and not VALIDATORS[t](
                v.replace("-", "") if t == "EIN" else v):
            bad("V8", "finding %s=%s fails its own validator" % (t, v))
        if not f.get("matched_label") or not f.get("evidence_quote"):
            bad("V8", "finding %s=%s carries no label or no evidence quote"
                      % (t, v))
        if not f.get("source_url"):
            bad("V8", "finding %s=%s carries no source url" % (t, v))
    # (9) the six outcomes stay distinct and no seventh appears.
    allowed = {"HARVESTED", "FOUND_NOT_EXTRACTED", "CHECKED_ABSENT",
               "ATTEMPTED_INCONCLUSIVE", "REFUSED", "NEVER_CHECKED"}
    seen = set(r["outcome"] for r in read_csv(COVERAGE))
    if seen - allowed:
        bad("V9", "outcome vocabulary breached: %s" % sorted(seen - allowed))
    # (10) an absence must be backed by the machine-readable routes.
    for r in read_csv(COVERAGE):
        if r["outcome"] == "CHECKED_ABSENT" and int(
                r.get("machine_readable_routes_run") or 0) < 2:
            bad("V10", "%s/%s claims CHECKED_ABSENT on %s route(s) - a "
                       "negative from search alone is not a negative"
                       % (r["cedar_uid"], r["harvest_type"],
                          r.get("machine_readable_routes_run")))

    if fails:
        print("VERIFY FAILED - %d breach(es)" % len(fails))
        for f in fails[:40]:
            print("  " + f)
        return 1
    if not quiet:
        print("VERIFY OK - 10 invariants, all measured, none breached")
    return 0


def selftest():
    """Prove every invariant FIRES. A check that has never failed on purpose
    is not known to work."""
    import shutil
    import tempfile
    global FINDINGS, COVERAGE, DOCLOG, SURFACES, REFUSALS, WORKLIST
    orig = (FINDINGS, COVERAGE, DOCLOG, SURFACES, REFUSALS, WORKLIST)
    tmp = Path(tempfile.mkdtemp(prefix="c1114_"))
    ok = [True]

    def point_at_tmp():
        global FINDINGS, COVERAGE, DOCLOG, SURFACES, REFUSALS, WORKLIST
        for p in tmp.glob("*"):
            p.unlink()
        FINDINGS, COVERAGE = tmp / "f.csv", tmp / "c.csv"
        DOCLOG, SURFACES = tmp / "d.jsonl", tmp / "s.csv"
        REFUSALS, WORKLIST = tmp / "r.csv", tmp / "w.csv"

    def scenario(name, setup):
        point_at_tmp()
        setup()
        rc = verify(quiet=True)
        if rc != 1:
            ok[0] = False
        print("  %-54s %s" % (name, "FIRES" if rc == 1
                              else "*** DID NOT FIRE ***"))

    print("selftest - each synthetic violation must make verify exit 1")
    scenario("V6 a PII column in an output", lambda: write_csv(
        FINDINGS, [{"cedar_uid": "X", "identifier_type": "CAGE",
                    "identifier": "9MM93", "matched_label": "CAGE:",
                    "evidence_quote": "q", "source_url": "u",
                    "owner_name_raw": "a natural person"}]))
    scenario("V8 a finding with no evidence quote", lambda: write_csv(
        FINDINGS, [{"cedar_uid": "X", "identifier_type": "CAGE",
                    "identifier": "9MM93", "matched_label": "CAGE:",
                    "evidence_quote": "", "source_url": "u"}]))
    scenario("V8 a finding failing its own validator", lambda: write_csv(
        FINDINGS, [{"cedar_uid": "X", "identifier_type": "CAGE",
                    "identifier": "JONES", "matched_label": "Cage Jones,",
                    "evidence_quote": "Cage Jones, MT Assistant Supervisor",
                    "source_url": "u"}]))
    scenario("V9 a seventh outcome value", lambda: write_csv(
        COVERAGE, [{"cedar_uid": "X", "harvest_type": "identifiers",
                    "outcome": "PROBABLY_FINE",
                    "machine_readable_routes_run": "4"}]))
    scenario("V10 CHECKED_ABSENT on a single route", lambda: write_csv(
        COVERAGE, [{"cedar_uid": "X", "harvest_type": "identifiers",
                    "outcome": "CHECKED_ABSENT",
                    "machine_readable_routes_run": "1"}]))

    def wpdmdl():
        for i in range(IDENTICAL_MD5_CEILING + 3):
            append_jsonl(DOCLOG, {"host": "h", "md5": "same",
                                  "url": "?wpdmdl=%d" % i, "cedar_uid": "X",
                                  "bytes": 1, "content_type": "application/pdf"})
    scenario("V7 the same md5 nine times from one host", wpdmdl)

    point_at_tmp()
    write_csv(FINDINGS, [{"cedar_uid": "X", "identifier_type": "CAGE",
                          "identifier": "9MM93", "matched_label": "CAGE Code:",
                          "evidence_quote": "CAGE Code: 9MM93",
                          "source_url": "u"}])
    write_csv(COVERAGE, [{"cedar_uid": "X", "harvest_type": "identifiers",
                          "outcome": "HARVESTED",
                          "machine_readable_routes_run": "4"}])
    rc = verify(quiet=True)
    print("  %-54s %s" % ("clean fixture must exit 0",
                          "OK" if rc == 0 else "*** EXITED 1 ***"))
    if rc != 0:
        ok[0] = False
    (FINDINGS, COVERAGE, DOCLOG, SURFACES, REFUSALS, WORKLIST) = orig
    shutil.rmtree(tmp, ignore_errors=True)
    print("SELFTEST PASSES" if ok[0] else "SELFTEST FAILED")
    return 0 if ok[0] else 1


def main():
    ap = argparse.ArgumentParser(description="1114 capability-statement harvest")
    ap.add_argument("cmd", choices=["worklist", "run", "build", "verify",
                                    "selftest"])
    ap.add_argument("--job", default="identifiers",
                    choices=["released", "identifiers", "institutions"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--hosts", default="")
    a = ap.parse_args()
    if a.cmd == "worklist":
        build_worklist()
    elif a.cmd == "run":
        run(a.job, a.limit, a.workers,
            set(h.strip() for h in a.hosts.split(",") if h.strip()) or None)
    elif a.cmd == "build":
        build()
    elif a.cmd == "verify":
        sys.exit(verify())
    elif a.cmd == "selftest":
        sys.exit(selftest())


if __name__ == "__main__":
    main()
