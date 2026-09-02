"""690_shard_m_vendor_list_sweep.py — WORKSTREAM SHARD-M, read-only discovery probe.

WHAT THIS IS
------------
The 2026-08-26 vendor-list survey checked 62 of 1,555 spine entities. 297 of the
349 federally recognized tribes had never been looked at. Shards L and M split
those 297 by `cedar_uid`; this script sweeps SHARD M — the second half, 149
tribes, `rem[148:]` where `rem` is the sorted remainder.

SELECTION DECLARATION
---------------------
Leg used            KNOWN_IDENTIFIER only (the spine's own federally-recognized
                    tribe list, minus tribes already carried in
                    review/tribal_vendor_list_registry_2026-08-26.csv).
Leg missing         No TYPE_FILTER exists for "tribe that publishes a vendor
                    list" — there is no registry of such lists to filter. The
                    universe here IS the spine's tribe list, so the identifier
                    leg is not a sample of a larger population; it is the
                    population. `population_basis` on every row emitted is
                    `spine_federally_recognized_tribe`.

WHAT IT DOES, PER HOST, IN THIS ORDER (the order is the point)
--------------------------------------------------------------
1. robots.txt          — record Disallow paths; never fetch one.
2. homepage            — verify the page NAMES THE TRIBE. Three tribal domains
                         were found hijacked on 2026-09-01 (wrpt.us now serves
                         adult video). A domain-name match is not evidence.
3. terms / legal page  — BEFORE any enumeration. docs/PULL_DISCIPLINE.md and the
                         NANA incident: a sibling stopped a sitemap run mid-way
                         on reading terms, at a cost of ~55 records, and that
                         was right. A host whose terms forbid it is dropped here
                         and NOTHING further is requested from it.
4. /wp-json/wp/v2/types— custom post types. Two tribal enterprise registers were
                         found on 2026-09-01 that exist ONLY as a CPT.
5. /wp-json/wp/v2/media— every uploaded PDF, including ones no page links to.
                         Paginated on X-WP-TotalPages, capped.
6. sitemap             — only where WordPress did not answer.

It WRITES NOTHING to data/clean and RESOLVES NO IDENTITY. Output is candidate
URLs for a human/agent read, plus the negative results, because a tribe with no
list is what makes the hit rate measurable.

Owns: data/staging/tribe_harvest/shard_m/** only.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse as up
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
SPINE = ROOT / "data" / "spine" / "cedar_identity_register.csv"
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"
WEBMAP_DIR = ROOT / "data" / "staging" / "tribe_web_map"
OUT = ROOT / "data" / "staging" / "tribe_harvest" / "shard_m"
RAW = OUT / "raw"
STATE = OUT / "_state.json"
CANDIDATES = OUT / "candidates.csv"
HOSTLOG = OUT / "host_log.jsonl"

UA = ("CedarPress-research/1.0 (tribal vendor-list survey; "
      "contact elijahsamsonmoreno@gmail.com)")
HEADERS = {"User-Agent": UA, "Accept": "*/*"}

PER_HOST_DELAY = 1.5      # seconds between requests to the SAME host
WORKERS = 4               # distinct hosts in flight; one poller per host
TIMEOUT = 25
MEDIA_PAGE_CAP = 25       # 1,200 media rows per host is plenty; see note below
RUN_DEADLINE_H = 2.0

# Hosts whose publisher has told us not to. These stay excluded by EVERY route,
# including Wayback and the media API. docs/HIDDEN_DATA_TECHNIQUES.md boundary.
TERMS_RESTRICTIVE_HOSTS = {
    "colvilletribes.com", "ctuir.org", "yakamanation-nsn.gov",
    "chickasaw.net", "nana.com", "akima.com", "southernute-nsn.gov",
    "fcpotawatomi.com", "fcpotawatomi-nsn.gov",
}

# A rendered page or a filename matching these is a candidate LIST.
LIST_PAT = re.compile(
    r"tero|tribal[\s\-_]*employment[\s\-_]*rights|indian[\s\-_]*preference|"
    r"indian[\s\-_]*owned|native[\s\-_]*owned|tribal(ly)?[\s\-_]*owned|"
    r"certified[\s\-_]*(vendor|business|contractor|firm)|"
    r"vendor[\s\-_]*(list|directory|registry|roster)|"
    r"(approved|preferred|certified)[\s\-_]*vendor|"
    r"business[\s\-_]*(licen[cs]e|directory|registry|register|listing)|"
    r"bidder[\s\-_]*list|contractor[\s\-_]*(list|directory|registry)|"
    r"chamber[\s\-_]*of[\s\-_]*commerce|"
    r"tribal[\s\-_]*(enterprise|business)[\s\-_]*(list|directory|registry)",
    re.I)

# Terms language that forbids automated copying. Deliberately broad — a false
# positive costs one tribe; a false negative costs the project's standing.
TERMS_FORBID_PAT = re.compile(
    r"may not (be )?(copy|reproduce|redistribut|extract|download|scrap)|"
    r"(no|not|prohibit\w*|forbid\w*)[^.]{0,80}"
    r"(scrap|crawl|spider|robot|automated (means|access|tool)|data ?min)|"
    r"(scrap|crawl|spider|harvest)\w*[^.]{0,60}(prohibit|forbid|not permitted|"
    r"without (our |the )?(prior |express )*written (permission|consent))|"
    r"all rights reserved[^.]{0,40}(no part|may not)|"
    r"unauthori[sz]ed (use|reproduction|copying|extraction)",
    re.I)

TERMS_PATHS = ["/terms", "/terms-of-use", "/terms-and-conditions",
               "/terms-of-service", "/legal", "/disclaimer",
               "/privacy-policy", "/copyright"]

CPT_SKIP = {"post", "page", "attachment", "nav_menu_item", "wp_block",
            "wp_template", "wp_template_part", "wp_navigation",
            "wp_font_family", "wp_font_face", "wp_global_styles",
            "revision", "menu-item", "custom_css", "customize_changeset",
            "oembed_cache", "user_request", "amp_validated_url"}


# Tribes in shard M for which NO sibling shard established a government URL.
# These are CANDIDATE hostnames only. Nothing here is treated as that tribe's
# site until sweep_host() confirms the served page names the tribe: wrpt.us, a
# lapsed tribal acronym now serving adult video, is why a domain-name match is
# never evidence. Sources for the candidates: URLs already present elsewhere in
# this repo (data/staging/cedar_web_map.csv, institution_registry) plus the
# -nsn.gov / -nsn.us conventions BIA registrants use. Unverified ones simply
# fail the name check and are recorded as NO_SITE_ESTABLISHED.
CANDIDATE_HOSTS = {
    "CE-00171-DJ": ["https://www.monacannation.com/"],                 # Monacan
    "CE-00176-BF": ["https://www.fortmojaveindiantribe.com/"],         # Fort Mojave
    "CE-0017D-NY": ["https://mashpeewampanoagtribe-nsn.gov/"],         # Mashpee
    "CE-0017K-SM": ["https://www.nansemond.org/"],                     # Nansemond
    "CE-0017P-BZ": ["https://northforkrancheria-nsn.gov/"],            # North Fork
    "CE-0017Q-HR": ["https://narragansettindiannation.org/"],          # Narragansett
    "CE-0017S-XA": ["https://www.nwbshoshone.com/"],                   # NW Shoshone
    "CE-0017Z-10": ["https://www.onondaganation.org/"],                # Onondaga
    "CE-00184-4D": ["https://pamunkey.org/"],                          # Pamunkey
    "CE-0018C-MN": ["https://www.resighinirancheria.com/"],            # Resighini
    "CE-0018J-RB": ["https://pojoaque.org/"],                          # Pojoaque
    "CE-0018M-4X": ["https://www.pbpindiantribe.com/"],                # Prairie Band
    "CE-0018R-W1": ["https://www.passamaquoddy.com/",
                    "https://sipayik.org/"],                           # Passamaquoddy
    "CE-0018T-8K": ["https://www.pottervalleytribe.com/"],             # Potter Valley
    "CE-0018V-EC": ["https://utahpaiutes.org/"],                       # Paiute of Utah
    "CE-00192-XB": ["https://quileutenation.org/"],                    # Quileute
    "CE-00194-9X": ["https://www.ramonatribe.com/"],                   # Ramona
    "CE-00195-FP": ["https://www.redding-rancheria.com/"],             # Redding
    "CE-00198-11": ["https://redwoodvalleyrancheria-nsn.gov/"],        # Redwood Valley
    "CE-00199-7T": ["https://rincon-nsn.gov/"],                        # Rincon
    "CE-0019B-KC": ["https://www.rsic.org/"],                          # Reno-Sparks
    "CE-0019D-ZY": ["https://www.chippewacree-nsn.gov/",
                    "https://chippewacree.org/"],                      # Chippewa-Cree
    "CE-0019F-BG": ["https://rappahannocktribe.org/"],                 # Rappahannock
    "CE-0019G-H9": ["https://www.samishtribe.nsn.us/"],                # Samish
    "CE-0019S-7A": ["https://scottsvalleyband.com/"],                  # Scotts Valley
    "CE-0019T-D3": ["https://www.kewa-nsn.us/"],                       # Santo Domingo
    "CE-0019X-ZE": ["https://www.shawnee-tribe.com/"],                 # Shawnee Tribe
    "CE-0019Z-B0": ["https://shinnecock-nsn.gov/"],                    # Shinnecock
    "CE-001A2-2V": ["https://www.sanipueblo.org/"],                    # San Ildefonso
    "CE-001A4-ED": ["https://www.skullvalleyband-nsn.gov/"],           # Skull Valley
    "CE-001A8-6H": ["https://www.summitlaketribe.org/"],               # Summit Lake
    "CE-001AE-A7": ["https://ohkayowingeh.org/",
                    "https://ohkay.org/"],                             # Ohkay Owingeh
    "CE-001B7-58": ["https://tejonindiantribe-nsn.gov/"],              # Tejon
    "CE-001C0-09": ["https://benton-paiute-nsn.gov/"],                 # Benton
    "CE-001C9-PA": ["https://winnemuccaindiancolony.com/"],            # Winnemucca
    "CE-001CH-6J": ["https://yombashoshonetribe.com/"],                # Yomba
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")



# ---------------------------------------------------------------- robots -----
#
# WHY THIS IS HAND-ROLLED AND NOT `urllib.robotparser`.
#
# Coordinator note 2026-09-01, measured by shard H, which lost 22 hosts to it:
# `RobotFileParser.read()` fetches robots.txt with the DEFAULT `Python-urllib`
# user agent, not ours. A host that blocks that UA answers 403, and the parser
# reads a 403 on robots.txt as `disallow_all`. The site looks closed when it is
# open. So robots.txt is fetched with the SAME UA that will fetch content, and
# a 404 / 403 / empty body is ALLOWED, not denied.
#
# The first version of this function had the mirror-image bug: it collected
# every `Disallow:` line in the file regardless of which `User-agent:` block it
# sat under. On 61 of 113 shard-M hosts that produced a `Disallow: /` that
# actually belonged to Baiduspider, Yandex, GPTBot, ClaudeBot or PetalBot.
# It happened to fail OPEN because the caller skipped a bare "/", but a rule
# read out of its group is not a rule, in either direction.

AI_DECLINE_UAS = {"gptbot", "claudebot", "ccbot", "google-extended", "anthropic-ai",
                  "meta-externalagent", "applebot-extended", "bytespider",
                  "perplexitybot", "cohere-ai", "diffbot", "omgili",
                  "facebookbot", "amazonbot", "timpibot", "youbot",
                  "img2dataset", "petalbot"}


def parse_robots(body, our_ua_token="cedarpress-research"):
    """Return (rules_for_us, ai_signals, groups_seen).

    rules_for_us: (allow, path) pairs from the group that binds US - an exact
    UA match if the file names us, otherwise the `*` group.
    ai_signals:   what the file says to declared AI crawlers, plus any
                  Content-Signal line. Recorded, never acted on here: whether a
                  research pull is covered by an AI-TRAINING decline is an owner
                  decision, not a scraper's.
    """
    groups, run, in_rules = {}, [], False
    signals = []
    for raw in (body or "").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            if in_rules:          # a new UA after rules starts a NEW group
                run, in_rules = [], False
            run.append(value.lower())
            groups.setdefault(value.lower(), [])
        elif field in ("allow", "disallow"):
            in_rules = True
            for ua in run:
                groups.setdefault(ua, []).append((field == "allow", value))
        elif field == "content-signal":
            signals.append(value)
    ai = [ua for ua, rules in groups.items()
          if ua in AI_DECLINE_UAS
          and any((not a) and pth == "/" for a, pth in rules)]
    mine = next((groups[ua] for ua in groups
                 if ua != "*" and our_ua_token in ua), None)
    if mine is None:
        mine = groups.get("*", [])
    return mine, {"ai_declined_uas": sorted(ai),
                  "content_signal": "; ".join(signals)}, sorted(groups)


def _robots_re(pattern):
    """robots.txt pattern -> regex. `*` is any run, `$` anchors the end."""
    out, anchored = [], pattern.endswith("$")
    for ch in (pattern[:-1] if anchored else pattern):
        out.append(".*" if ch == "*" else re.escape(ch))
    return re.compile("^" + "".join(out) + ("$" if anchored else ""))


def path_blocked(rules, path):
    """Longest-pattern-match Allow/Disallow, with wildcards.

    The first version compared only the literal prefix before the first `*`.
    On a Squarespace robots.txt (`Disallow: /*&format=json`) that prefix is
    "/", so EVERY path looked disallowed and 12 shard-M hosts were recorded as
    blocking the media API when none of them do. A wildcard rule that is not
    matched as a wildcard is a phantom block, and a phantom block is
    indistinguishable in the output from a tribe that publishes nothing.
    """
    best_len, best_allow = -1, True
    for allow, pat in rules:
        if not pat:
            continue
        if _robots_re(pat).match(path) and len(pat) > best_len:
            best_len, best_allow = len(pat), allow
    return best_len >= 0 and not best_allow


# ---------------------------------------------------------------- selection --

def load_shard_m():
    spine = list(csv.DictReader(SPINE.open(encoding="utf-8")))
    fed = [r for r in spine if r["entity_class"] == "Federally recognized tribe"]
    already = {r["tribe_id"] for r in
               csv.DictReader(REGISTRY.open(encoding="utf-8"))}
    rem = sorted((r for r in fed if r["handle"] not in already),
                 key=lambda r: r["cedar_uid"])
    # Second half. The split point is n//2 so that shard M's slice starts at or
    # BEFORE shard L's end: a one-tribe overlap produces a duplicate registry
    # row, which is visible and cheap; a one-tribe gap is invisible and is the
    # exact failure this survey exists to close.
    return rem[len(rem) // 2:]


def load_webmap(uids):
    """Government/list URLs sibling shards already established, with evidence."""
    by_uid = {u: [] for u in uids}
    for path in sorted(WEBMAP_DIR.glob("shard_*.csv")):
        for row in csv.DictReader(path.open(encoding="utf-8")):
            uid = row.get("cedar_uid", "")
            if uid in by_uid:
                by_uid[uid].append(row)
    return by_uid


# ------------------------------------------------------------------ fetching --

class HostSession:
    """One session per host. Sequential, delayed, and it counts its own budget."""

    def __init__(self, host):
        self.host = host
        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        self.last = 0.0
        self.n = 0
        self.errors = []

    def get(self, url, allow_binary=False):
        wait = PER_HOST_DELAY - (time.time() - self.last)
        if wait > 0:
            time.sleep(wait)
        self.last = time.time()
        self.n += 1
        try:
            r = self.s.get(url, timeout=TIMEOUT, allow_redirects=True,
                           stream=allow_binary)
            body = r.content if allow_binary else None
            text = "" if allow_binary else r.text
            return {"ok": True, "status": r.status_code, "url": r.url,
                    "headers": {k.lower(): v for k, v in r.headers.items()}, "text": text, "body": body}
        except requests.RequestException as exc:
            shape = type(exc).__name__
            self.errors.append(f"{url} :: {shape}")
            return {"ok": False, "status": shape, "url": url,
                    "headers": {}, "text": "", "body": None}


def name_tokens(canonical_name):
    words = re.findall(r"[A-Za-z']{4,}", canonical_name)
    stop = {"tribe", "tribes", "band", "nation", "indian", "indians",
            "pueblo", "community", "rancheria", "reservation", "tribal",
            "confederated", "the", "of", "and"}
    toks = [w.lower() for w in words if w.lower() not in stop]
    return toks or [w.lower() for w in words]


def verify_names_tribe(html, canonical_name):
    """A domain-name match is not evidence. The PAGE must name the tribe."""
    low = re.sub(r"<[^>]+>", " ", html or "").lower()
    toks = name_tokens(canonical_name)
    hits = [t for t in toks if t in low]
    return hits, toks


# Word-bounded on purpose: an unanchored /cialis/ matched "Case Specialist" on
# modocnation.com and flagged a live tribal government site as hijacked.
HIJACK_PAT = re.compile(
    r"\b(porn|xxx|viagra|cialis|escorts?|slot ?gacor|judi bola|"
    r"casino bonus codes?|betting sites?|situs togel)\b", re.I)


# ------------------------------------------------------------------ per host --

def sweep_host(job, stage7_only=False, prior=None):
    """job = {uid, handle, name, base, hot_urls}. Returns one record."""
    uid, name, base = job["uid"], job["name"], job["base"]
    host = up.urlsplit(base).netloc.lower()
    rec = {"cedar_uid": uid, "handle": job["handle"], "canonical_name": name,
           "robots_ai_declined": [], "robots_content_signal": "",
           "base_url": base, "host": host, "checked_date": now_iso()[:10],
           "robots_note": "", "terms_status": "NOT_CHECKED",
           "terms_url": "", "terms_quote": "",
           "homepage_status": "", "names_tribe": "", "hijack_flag": "N",
           "wp": "N", "wp_types": [], "media_pdf_n": 0, "media_pages": 0,
           "candidates": [], "requests_made": 0, "errors": []}

    if host in TERMS_RESTRICTIVE_HOSTS or any(
            host.endswith("." + h) for h in TERMS_RESTRICTIVE_HOSTS):
        rec["terms_status"] = "TERMS_STATED_RESTRICTIVE"
        rec["terms_quote"] = "known-restrictive host list; excluded by every route"
        return rec

    if stage7_only:
        # Terms were read on the first pass; a second read would be one more
        # request for an answer already on disk. A host the first pass could
        # not clear is not cleared now either.
        if not prior:
            rec["terms_status"] = "NO_PRIOR_PROBE"
            return rec
        rec.update({k: prior.get(k, rec[k]) for k in
                    ("robots_note", "terms_status", "terms_url", "terms_quote",
                     "homepage_status", "names_tribe", "hijack_flag", "wp",
                     "media_pdf_n", "media_pages")})
        if rec["terms_status"] == "TERMS_STATED_RESTRICTIVE" or                 rec["hijack_flag"] == "Y":
            return rec

    sess = HostSession(host)
    root = f"{up.urlsplit(base).scheme}://{host}"

    # 1 -- robots.txt, fetched with OUR user agent and parsed BY GROUP.
    #      A 404/403/empty body is ALLOWED, not denied: see parse_robots.
    rules = []
    if stage7_only:
        rules = [(False, d) for d in
                 (prior.get("robots_note", "") or "")
                 .replace("our group (*): Disallow ", "").split("; ")
                 if d.startswith("/")]
        rec["robots_note"] = prior.get("robots_note", "")
    else:
        r = sess.get(root + "/robots.txt")
        body = ""
        if r["ok"] and r["status"] == 200 and "text/html" not in                 r["headers"].get("content-type", ""):
            body = r["text"]
        rules, ai, _ = parse_robots(body)
        dis = [pth for allow, pth in rules if not allow and pth]
        rec["robots_note"] = (
            ("our group (*): Disallow " + "; ".join(sorted(set(dis))[:14]))
            if dis else "our group (*): no Disallow directives")
        if not body:
            rec["robots_note"] = f"robots.txt {r['status']} - treated as ALLOWED"
        rec["robots_ai_declined"] = ai["ai_declined_uas"]
        rec["robots_content_signal"] = ai["content_signal"]

    def blocked(path):
        return path_blocked(rules, path)

    # 2 -- homepage, and does it name the tribe
    r = ({"ok": False, "status": "reused", "text": "", "headers": {}}
         if stage7_only else sess.get(base))
    rec["homepage_status"] = r["status"]
    html = r["text"] if r["ok"] else ""
    if r["ok"] and r["status"] == 200:
        hits, toks = verify_names_tribe(html, name)
        rec["names_tribe"] = ("YES: " + ",".join(hits[:4])) if hits else \
            f"NO — page does not contain any of {toks[:4]}"
        if HIJACK_PAT.search(html):
            rec["hijack_flag"] = "Y"
            rec["errors"] = sess.errors
            rec["requests_made"] = sess.n
            return rec
        if not hits:
            # Flagged, not skipped. Some tribal homepages render the name only
            # in JS; the flag makes the candidate un-harvestable until a human
            # confirms the page names the tribe, which is the actual guard.
            rec["hijack_flag"] = "UNVERIFIED"

    # 3 -- TERMS, before anything is enumerated
    tried = []
    if stage7_only:
        html = ""
    for p in ([] if stage7_only else TERMS_PATHS):
        if blocked(p):
            continue
        # only follow terms links the homepage actually offers, plus /terms*
        if p not in ("/terms", "/terms-of-use") and \
                p.strip("/") not in (html or "").lower():
            continue
        tried.append(p)
        tr = sess.get(root + p)
        if not (tr["ok"] and tr["status"] == 200):
            continue
        txt = re.sub(r"<script.*?</script>", " ", tr["text"], flags=re.S | re.I)
        txt = re.sub(r"<[^>]+>", " ", txt)
        txt = re.sub(r"\s+", " ", txt)
        m = TERMS_FORBID_PAT.search(txt)
        if m:
            s = max(0, m.start() - 120)
            rec["terms_status"] = "TERMS_STATED_RESTRICTIVE"
            rec["terms_url"] = tr["url"]
            rec["terms_quote"] = txt[s:m.end() + 160].strip()[:600]
            rec["requests_made"] = sess.n
            rec["errors"] = sess.errors
            return rec
        rec["terms_status"] = "TERMS_READ_PERMISSIVE"
        rec["terms_url"] = tr["url"]
        break
    if rec["terms_status"] == "NOT_CHECKED" and not stage7_only:
        rec["terms_status"] = "SILENT_NO_TERMS_PAGE_FOUND"
        rec["terms_quote"] = "paths probed: " + ",".join(tried) if tried else \
            "no terms/legal link offered by the homepage"

    # 4 -- WordPress custom post types
    if not stage7_only and not blocked("/wp-json"):
        tr = sess.get(root + "/wp-json/wp/v2/types")
        if tr["ok"] and tr["status"] == 200:
            try:
                types = json.loads(tr["text"])
            except ValueError:
                types = {}
            if isinstance(types, dict) and types:
                rec["wp"] = "Y"
                for slug, meta in types.items():
                    if slug in CPT_SKIP or not isinstance(meta, dict):
                        continue
                    label = str(meta.get("name", "")) + " " + slug
                    rec["wp_types"].append(slug)
                    if LIST_PAT.search(label):
                        ep = (meta.get("_links", {}) or {}).get("wp:items", [{}])
                        href = ep[0].get("href") if ep else None
                        rec["candidates"].append({
                            "kind": "wp_custom_post_type",
                            "url": (href or
                                    f"{root}/wp-json/wp/v2/{slug}") + "?per_page=100",
                            "title": label.strip(),
                            "technique": "wp-json /types -> custom post type",
                        })

    # 5 -- every uploaded PDF, linked or not
    if not stage7_only and rec["wp"] == "Y" and not blocked("/wp-json"):
        page, total = 1, 1
        while page <= total and page <= MEDIA_PAGE_CAP:
            mu = (f"{root}/wp-json/wp/v2/media?per_page=100&page={page}"
                  f"&mime_type=application/pdf&_fields=id,source_url,title,date,"
                  f"modified")
            mr = sess.get(mu)
            if not (mr["ok"] and mr["status"] == 200):
                break
            try:
                items = json.loads(mr["text"])
            except ValueError:
                break
            if not isinstance(items, list) or not items:
                break
            total = int(mr["headers"].get("x-wp-totalpages", 1) or 1)
            rec["media_pages"] = total
            rec["media_pdf_n"] += len(items)
            for it in items:
                su = it.get("source_url", "") or ""
                ti = ((it.get("title") or {}).get("rendered") or "")
                if LIST_PAT.search(su) or LIST_PAT.search(ti):
                    rec["candidates"].append({
                        "kind": "wp_media_pdf", "url": su,
                        "title": re.sub(r"<[^>]+>", "", ti).strip(),
                        "date": it.get("date", ""),
                        "modified": it.get("modified", ""),
                        "technique": "wp-json /media enumeration (unlinked PDFs)",
                    })
            page += 1

    # 6 -- sitemap, only where WordPress did not answer
    if not stage7_only and rec["wp"] != "Y":
        for sm in ("/sitemap_index.xml", "/sitemap.xml", "/sitemap-1.xml"):
            if blocked(sm):
                continue
            sr = sess.get(root + sm)
            if not (sr["ok"] and sr["status"] == 200 and "<" in sr["text"]):
                continue
            locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", sr["text"])
            subs = [l for l in locs if l.endswith(".xml")][:8]
            for sub in subs:
                s2 = sess.get(sub)
                if s2["ok"] and s2["status"] == 200:
                    locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", s2["text"])
            for l in dict.fromkeys(locs):
                if l.endswith(".xml"):
                    continue
                if LIST_PAT.search(l):
                    rec["candidates"].append({
                        "kind": "sitemap_url", "url": l, "title": "",
                        "technique": "sitemap.xml enumeration",
                    })
            break

    # 7 -- the TERO / procurement / licence URLs sibling shards already
    #      established with evidence. Reusing them is the point of the web map;
    #      rediscovering them would be a second crawl for the same bytes.
    for hot in job.get("hot_urls", []):
        u = hot["url"]
        if not u.startswith("http") or "web.archive.org" in u:
            continue
        if blocked(up.urlsplit(u).path):
            continue
        hr = sess.get(u)
        if not (hr["ok"] and hr["status"] == 200):
            rec["candidates"].append({
                "kind": "webmap_" + hot["url_type"], "url": u,
                "title": f"(sibling-shard URL, refetch {hr['status']})",
                "technique": "tribe_web_map URL, re-fetched"})
            continue
        ct = hr["headers"].get("content-type", "")
        if "json" in ct:
            n = hr["text"].count('"id"')
            rec["candidates"].append({
                "kind": "webmap_" + hot["url_type"], "url": u,
                "title": f"JSON endpoint, ~{n} objects",
                "technique": "tribe_web_map custom-post-type endpoint"})
            continue
        txt = re.sub(r"<[^>]+>", " ", hr["text"])
        docs = re.findall(
            r'href=["\']([^"\']+\.(?:pdf|xlsx?|csv|docx?))["\']',
            hr["text"], re.I)
        rec["candidates"].append({
            "kind": "webmap_" + hot["url_type"], "url": u,
            "title": (re.search(r"<title[^>]*>(.*?)</title>", hr["text"],
                                re.S | re.I) or [None, ""])[1].strip()[:120],
            "technique": "tribe_web_map URL, re-fetched",
            "linked_docs": ";".join(up.urljoin(u, d) for d in docs[:12]),
            "page_chars": len(txt)})
        for d in docs[:12]:
            full = up.urljoin(u, d)
            if LIST_PAT.search(full):
                rec["candidates"].append({
                    "kind": "linked_document", "url": full, "title": "",
                    "technique": "document linked from a tribe_web_map URL"})

    rec["requests_made"] = sess.n
    rec["errors"] = sess.errors[:8]
    return rec



# ---------------------------------------------------------------- --fetch ----

def fetch_shortlist(path):
    """Download the curated shortlist to raw/, one host at a time, rate-limited.

    Input CSV: cedar_uid,handle,canonical_name,label,url. The shortlist is the
    OUTPUT of the sweep, hand-read; this step exists so the bytes we parsed are
    on disk with a manifest, not re-fetched by whoever checks the numbers.
    A host whose terms the sweep found restrictive is refused here too.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    refuse = set()
    if HOSTLOG.exists():
        for line in HOSTLOG.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("terms_status") == "TERMS_STATED_RESTRICTIVE" or                     r.get("hijack_flag") == "Y":
                refuse.add(r["host"])
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    by_host = {}
    for r in rows:
        by_host.setdefault(up.urlsplit(r["url"]).netloc.lower(), []).append(r)
    manifest = []
    for host, group in by_host.items():
        if host in refuse or host in TERMS_RESTRICTIVE_HOSTS:
            for r in group:
                manifest.append({**r, "status": "REFUSED_TERMS_OR_HIJACK",
                                 "path": "", "bytes": 0})
                print(f"  REFUSED {host} {r['label']}")
            continue
        sess = HostSession(host)
        for r in group:
            resp = sess.get(r["url"], allow_binary=True)
            if not (resp["ok"] and resp["status"] == 200):
                manifest.append({**r, "status": str(resp["status"]),
                                 "path": "", "bytes": 0})
                print(f"  {resp['status']} {r['url']}")
                continue
            ext = os.path.splitext(up.urlsplit(r["url"]).path)[1][:6] or ".bin"
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", r["label"])[:70]
            fp = RAW / f"{r['cedar_uid']}_{safe}{ext}"
            fp.write_bytes(resp["body"])
            manifest.append({**r, "status": "200", "path": str(
                fp.relative_to(ROOT)), "bytes": len(resp["body"]),
                "content_type": resp["headers"].get("content-type", ""),
                "last_modified": resp["headers"].get("last-modified", "")})
            print(f"  200 {len(resp['body']):9d}  {fp.name}")
    mf = OUT / "fetch_manifest.csv"
    cols = ["cedar_uid", "handle", "canonical_name", "label", "url", "status",
            "path", "bytes", "content_type", "last_modified"]
    exists = mf.exists()
    with mf.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        if not exists:
            w.writeheader()
        for m in manifest:
            w.writerow(m)
    print(f"manifest -> {mf}  ({sum(1 for m in manifest if m['status']=='200')}"
          f"/{len(manifest)} retrieved)")
    return 0



def dump_media(only_wp=True):
    """Re-run stage 5 and WRITE EVERY PDF URL, not just the keyword matches.

    The first pass kept only LIST_PAT hits, which means the keyword list itself
    became the limit of what could ever be found on these hosts and nobody
    could widen it without re-fetching. 31,393 PDFs were enumerated and 108
    kept. This writes the whole enumeration to disk once so the next agent
    greps a file instead of re-requesting 70 tribal servers.
    """
    prior = {}
    for line in HOSTLOG.open(encoding="utf-8"):
        r = json.loads(line)
        prior[r["cedar_uid"]] = r
    todo = [r for r in prior.values()
            if r.get("wp") == "Y"
            and r.get("terms_status") != "TERMS_STATED_RESTRICTIVE"
            and r.get("hijack_flag") != "Y"
            and r.get("host") not in TERMS_RESTRICTIVE_HOSTS]
    out = OUT / "media_inventory.csv"
    print(f"media dump: {len(todo)} WordPress hosts")
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cedar_uid", "canonical_name", "host", "source_url",
                    "title", "date", "modified"])

        def one(rec):
            rows, sess = [], HostSession(rec["host"])
            root = "https://" + rec["host"]
            page, total = 1, 1
            while page <= total and page <= MEDIA_PAGE_CAP:
                mr = sess.get(f"{root}/wp-json/wp/v2/media?per_page=100"
                              f"&page={page}&mime_type=application/pdf"
                              f"&_fields=source_url,title,date,modified")
                if not (mr["ok"] and mr["status"] == 200):
                    break
                try:
                    items = json.loads(mr["text"])
                except ValueError:
                    break
                if not isinstance(items, list) or not items:
                    break
                total = int(mr["headers"].get("x-wp-totalpages", 1) or 1)
                for it in items:
                    rows.append([rec["cedar_uid"], rec["canonical_name"],
                                 rec["host"], it.get("source_url", ""),
                                 re.sub(r"<[^>]+>", "",
                                        (it.get("title") or {}).get(
                                            "rendered", "")).strip(),
                                 it.get("date", ""), it.get("modified", "")])
                page += 1
            return rows

        n = 0
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for rows in ex.map(one, todo):
                for r in rows:
                    w.writerow(r)
                n += len(rows)
                fh.flush()
                if rows:
                    print(f"  {rows[0][1][:30]:30s} {len(rows):5d}", flush=True)
    print(f"{n} PDF rows -> {out}")
    return 0



def recheck_robots():
    """Re-derive robots for every host with the UA-GROUPED parser.

    The first pass collected Disallow lines without regard to which
    `User-agent:` block they sat under and produced a `Disallow: /` on 61 of
    113 hosts that belonged to Baiduspider, Yandex, GPTBot, ClaudeBot or
    PetalBot. It failed open, so nothing was wrongly skipped and nothing
    wrongly fetched - but a rule read out of its group is not a rule, and a
    hit rate measured against phantom blocks is not a hit rate.
    """
    prior = [json.loads(l) for l in HOSTLOG.open(encoding="utf-8")]
    out = OUT / "robots_recheck.csv"

    def one(rec):
        host = rec["host"]
        if host in TERMS_RESTRICTIVE_HOSTS or                 rec.get("terms_status") == "TERMS_STATED_RESTRICTIVE":
            return [rec["cedar_uid"], rec["canonical_name"], host,
                    "NOT_REFETCHED_TERMS_RESTRICTIVE", "", "", ""]
        sess = HostSession(host)
        r = sess.get("https://" + host + "/robots.txt")
        body = ""
        if r["ok"] and r["status"] == 200 and                 "text/html" not in r["headers"].get("content-type", ""):
            body = r["text"]
        (RAW / "robots").mkdir(parents=True, exist_ok=True)
        (RAW / "robots" / (host + ".txt")).write_text(body, encoding="utf-8")
        rules, ai, groups = parse_robots(body)
        dis = [pth for allow, pth in rules if not allow and pth]
        note = ("our group (*): Disallow " + "; ".join(sorted(set(dis))[:14])
                if dis else "our group (*): no Disallow directives")
        if not body:
            note = f"robots.txt {r['status']} - treated as ALLOWED"
        return [rec["cedar_uid"], rec["canonical_name"], host, note,
                "Y" if path_blocked(rules, "/wp-json/wp/v2/media") else "N",
                ";".join(ai["ai_declined_uas"]), ai["content_signal"]]

    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cedar_uid", "canonical_name", "host", "robots_note",
                    "media_api_blocked", "ai_declined_uas", "content_signal"])
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for row in ex.map(one, prior):
                w.writerow(row)
                fh.flush()
    print(f"robots recheck -> {out}")
    return 0



# ---------------------------------------------------------------- --harvest --
#
# Three sources, three shapes: a Word document, a four-page SCAN needing OCR,
# and a machine-extractable PDF table. Each parser records the characters it
# actually extracted per document, because a truncated read reports "no
# content" and is indistinguishable from a document that has none - which for
# this workstream would turn a real vendor list into a false CAPTURED_NOT_PARSED.
#
# PRIVACY. Owner names, e-mails, phones and street addresses are carried in
# STAGING ONLY. They exist here because the publisher printed them and because
# `owner_name_present` / `n_owners_named` cannot be computed without them.
# Nothing in this file may reach data/clean unfiltered, and a firm whose legal
# name IS a natural person's name is flagged so a consumer can suppress it.

BUSREG = ROOT / "data" / "staging" / "business_registry"
RUN_ID = "run-2026-09-01-shard-m"
STAMP = "2026-09-01T00:00:00Z"

PERSON_NAME_RE = re.compile(
    r"^[A-Z][a-z'\-]+(\s+[A-Z]\.?)?\s+[A-Z][a-z'\-]+"
    r"(\s+(Jr\.?|Sr\.?|I{2,3}))?$")
SUFFIX_RE = re.compile(
    r"\b(llc|l\.l\.c|inc|incorporated|corp|corporation|co\b|company|ltd|"
    r"lp|llp|pllc|plc|enterprises?|group|services?|construction|"
    r"contracting|associates|holdings|partners|solutions|systems|"
    r"industries|supply|trucking|consulting)\b", re.I)


def _person_name_flag(name):
    """1 = the business name IS a natural person's name, 0 = not, -1 = unclear."""
    n = (name or "").strip().rstrip(",.")
    if not n:
        return -1
    if SUFFIX_RE.search(n):
        return 0
    if PERSON_NAME_RE.match(n):
        return 1
    return -1


def _norm(name):
    n = (name or "").lower()
    n = re.sub(r"[^a-z0-9&' ]+", " ", n)
    n = re.sub(r"\b(llc|l l c|inc|incorporated|corp|corporation|co|company|"
               r"ltd|lp|llp|pllc)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def _row(source_id, nation_id, name, **kw):
    key = hashlib.sha256(
        (source_id + "|" + (name or "") + "|" +
         (kw.get("owner_name_raw") or "")).encode("utf-8")).hexdigest()[:10]
    base = {
        "business_source_id": f"{source_id}:{key}", "source_id": source_id,
        "source_business_key": key, "business_entity_id": None,
        "nation_id": nation_id, "business_name_raw": name,
        "business_name_normalized": _norm(name),
        "business_name_is_person_name": _person_name_flag(name),
        "dba_name": None, "owner_name_raw": None,
        "directory_type": None, "identity_scope": None,
        "identity_claim_text": None, "ownership_percent": None,
        "ownership_threshold_min": None, "control_requirement": None,
        "tribal_affiliation_raw": None, "verification_basis": None,
        "certification_number": None, "certification_tier": None,
        "certification_start": None, "certification_expiration": None,
        "business_license_number": None, "service_category_raw": None,
        "naics": None, "description_raw": None, "address_raw": None,
        "city": None, "state_province": None, "postal_code": None,
        "phone": None, "email": None, "website": None,
        "source_url": None, "source_edition": None,
        "first_seen": STAMP, "last_seen": STAMP, "source_last_updated": None,
        "is_current": True, "validation_flags": [], "ingestion_method": None,
        "ocr_mean_confidence": None, "raw_snapshot_uri": None,
        "refresh_run_id": RUN_ID, "relationship_basis_raw": None,
        "relationship_basis": "unspecified", "certification_event_status": None,
        "source_priority_class": "tribal_primary", "cross_reference_only": False,
        "matched_primary_source_ids": None, "match_method": None,
        "match_confidence": None, "assertion_precedence_rank": 1,
        "population_basis": "spine_federally_recognized_tribe",
    }
    base.update(kw)
    base["record_hash"] = "sha256:" + hashlib.sha256(
        json.dumps({k: v for k, v in base.items() if k != "record_hash"},
                   sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return base


# ---- TBD-M01  Spokane Tribe of Indians -------------------------------------

SPOKANE_URL = ("https://www.spokanetribe.com/wp-content/uploads/2026/06/"
               "UPDATED-INDIAN-PREFERENCE-COMPANIES-LIST-06-25-2026.docx")
SPOKANE_CLAIM = (
    "Spokane Tribe of Indians, Tribal Employment Rights Office. Document "
    "title: 'UPDATED INDIAN PREFERENCE COMPANIES LIST 06-25-2026'; document "
    "heading, verbatim: 'LOCAL COMPANIES LOCATED ON OR NEAR THE RESERVATION "
    "WITH INDIAN PREFERENCE QUALIFICATIONS'. The list is divided by the "
    "publisher into two sections: 'Spokane Tribal Owned Companies or "
    "Enterprises:' and 'Other Indian Owned Companies'.")


def harvest_spokane():
    import docx
    src = RAW / ("CE-001AK-84_spokane_indian_preference_companies_list_"
                 "06-25-2026.docx")
    doc = docx.Document(src)
    paras = [p.text.replace(" ", " ").strip() for p in doc.paragraphs]
    chars = sum(len(p) for p in paras)
    sec1 = next(i for i, p in enumerate(paras)
                if p.lower().startswith("spokane tribal owned companies"))
    sec2 = next(i for i, p in enumerate(paras)
                if p.lower().startswith("other indian owned companies"))
    blocks, cur, section = [], [], None
    for i, p in enumerate(paras):
        if i == sec1:
            section, cur = "spokane_tribal_owned", []
            continue
        if i == sec2:
            if cur:
                blocks.append((section, cur))
            section, cur = "other_indian_owned", []
            continue
        if section is None:
            continue
        if not p:
            if cur:
                blocks.append((section, cur))
                cur = []
            continue
        cur.append(p)
    if cur:
        blocks.append((section, cur))

    rows = []
    for section, lines in blocks:
        head = lines[0]
        parts = re.split(r"\s+[–—-]\s+", head, maxsplit=1)
        name = parts[0].strip().rstrip(",")
        svc = parts[1].strip() if len(parts) > 1 else None
        owner, phones, emails, sites, addr = None, [], [], [], []
        is_enterprise = False
        for ln in lines[1:]:
            low = ln.lower()
            if "tribal enterprise" in low:
                is_enterprise = True
                continue
            if "@" in ln:
                emails.append(ln.strip())
                continue
            if re.search(r"\(?\d{3}\)?\s*[\-–.]?\s*\d{3}\s*[\-–.]\s*\d{4}", ln):
                phones.append(re.sub(r"^(Office|Cell)\s+", "", ln).strip())
                continue
            if re.match(r"^[a-z0-9.\-]+\.(com|org|net)$", low):
                sites.append(ln.strip())
                continue
            if re.search(r"[A-Z]{2}\s+\d{5}", ln) or \
                    re.match(r"^(P\.?O\.?\s*Box|\d{2,6}\s)", ln, re.I):
                addr.append(ln.strip())
                continue
            # An owner line is a PERSON, or says so. The first version took
            # any non-address line, so "Environmental Consulting" - the second
            # half of a wrapped service description - became White Shield
            # Inc.'s owner. A field that can absorb anything is not a field.
            role = re.search(r"[–—-]\s*(Owner|Chairman|President|"
                             r"General Manager|Superintendent|Management)",
                             ln, re.I)
            looks_personal = re.match(
                r"^[A-Z][A-Za-z'\.\-]+(\s+[A-Z][A-Za-z'\.\-]*)"
                r"{1,3}(\s*/\s*[A-Z][A-Za-z'\.\-]+.*)?$", ln)
            if owner is None and (role or looks_personal) and                     not re.match(r"^\d", ln):
                owner = re.split(r"\s*[–—-]\s*|\s*\(", ln)[0].strip()
                continue
            if svc and not role and not looks_personal:
                svc = (svc + " " + ln).strip()
                continue
            addr.append(ln.strip())
        city = state = zipc = None
        for a in addr:
            m = re.search(r"^(.*?),\s*([A-Z]{2})\s+(\d{5})", a)
            if m:
                city, state, zipc = m.group(1).strip(), m.group(2), m.group(3)
        flags = ["no_ownership_percent_threshold_certification_number_or_"
                 "expiry_anywhere_in_the_source",
                 "section_header_is_the_only_identity_claim_the_publisher_makes"]
        if section == "spokane_tribal_owned":
            scope = "tribally_owned_entity" if is_enterprise else "mixed"
            if scope == "mixed":
                flags.append(
                    "identity_scope=mixed: the publisher's section header is "
                    "'Spokane Tribal Owned Companies or Enterprises' and does "
                    "NOT distinguish, per row, a firm owned by the Tribe from "
                    "a firm owned by a Spokane citizen. Rows that name "
                    "themselves a 'Spokane Tribal Enterprise' are typed "
                    "tribally_owned_entity; the rest are not resolvable from "
                    "the document.")
        else:
            scope = "any_native"
            flags.append(
                "identity_scope=any_native: section header 'Other Indian "
                "Owned Companies' asserts Indian ownership and does NOT "
                "assert Spokane membership.")
        rows.append(_row(
            "TBD-M01", "cedar:TRBF-SPKANE-00", name,
            owner_name_raw=owner, directory_type="indian_preference",
            identity_scope=scope,
            identity_claim_text=SPOKANE_CLAIM + " Section: " + (
                "Spokane Tribal Owned Companies or Enterprises"
                if section == "spokane_tribal_owned"
                else "Other Indian Owned Companies"),
            verification_basis="TERO_review",
            service_category_raw=svc, description_raw=svc,
            address_raw="; ".join(addr) or None, city=city,
            state_province=state, postal_code=zipc,
            phone="; ".join(phones) or None, email="; ".join(emails) or None,
            website="; ".join(sites) or None,
            source_url=SPOKANE_URL,
            source_edition="UPDATED-INDIAN-PREFERENCE-COMPANIES-LIST-"
                           "06-25-2026.docx",
            source_last_updated="2026-06-25",
            ingestion_method="docx",
            raw_snapshot_uri=str(src.relative_to(ROOT)).replace("\\", "/"),
            relationship_basis="member" if section == "spokane_tribal_owned"
            else "indian_owned",
            certification_event_status="listed",
            validation_flags=flags))
    return "TBD-M01", "spokane_indian_preference_companies_list", rows, chars


# ---- TBD-M02  Sisseton-Wahpeton Oyate --------------------------------------

SWO_URL = ("https://swo-nsn.gov/media/amhdcytc/"
           "tero-indian-preference-list-1-2025-1.pdf")
SWO_CLAIM = (
    "Sisseton-Wahpeton Oyate, Tribal Employment Rights Office, P.O. Box 509, "
    "Agency Village, South Dakota 57262. Document heading, verbatim: "
    "'APPROVED INDIAN PREFERENCE BUSINESSES'; 'UPDATED: January 14, 2025'. "
    "Column headings, verbatim: 'Business Name / Date to Update', "
    "\"Owner's Name / Phone\", 'Address', 'Type of Business'.")


def harvest_swo():
    import fitz
    import numpy as np
    from PIL import Image
    from rapidocr_onnxruntime import RapidOCR
    src = RAW / "CE-001B3-D4_swo_tero_indian_preference_list_1-2025.pdf"
    ocr = RapidOCR()
    doc = fitz.open(src)
    rows, confs, chars = [], [], 0
    for pno, page in enumerate(doc):
        pix = page.get_pixmap(dpi=220)
        img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        res, _ = ocr(np.array(img))
        if not res:
            continue
        items = []
        for box, text, conf in res:
            y = sum(pt[1] for pt in box) / 4.0
            x = min(pt[0] for pt in box)
            items.append((y, x, float(conf), text.strip()))
            confs.append(float(conf))
            chars += len(text)
        items.sort()
        lines, cur, last = [], [], None
        for y, x, c, t in items:
            if last is not None and y - last > 14:
                lines.append(sorted(cur, key=lambda r: r[1]))
                cur = []
            cur.append((y, x, c, t))
            last = y
        if cur:
            lines.append(sorted(cur, key=lambda r: r[1]))
        starts = [i for i, ln in enumerate(lines)
                  if ln and ln[0][1] < 320 and re.match(r"UPDATED", ln[0][3],
                                                        re.I)]
        for si, start in enumerate(starts):
            end = starts[si + 1] if si + 1 < len(starts) else len(lines)
            c1, c2, c3, c4 = [], [], [], []
            for ln in lines[start:end]:
                for y, x, c, t in ln:
                    (c1 if x < 400 else c2 if x < 800 else
                     c3 if x < 1300 else c4).append(t)
            name = next((t for t in c1
                         if not re.match(r"(UPDATED|THRU|Sw[o0]|SW[O0])", t,
                                         re.I)), None)
            if not name:
                continue
            if re.search(r"Business\s*Name|Date to Update", name, re.I) or                     re.search(r"Type of Business", " ".join(c4), re.I):
                continue      # the column-heading band, not a record
            upd = next((m.group(1) for t in c1
                        for m in [re.search(r"UPDATED:?\s*([\d\-/.]+)", t,
                                            re.I)] if m), None)
            thru = next((m.group(1) for t in c1
                         for m in [re.search(r"THRU\s*:?\s*([\d\-/.]+)", t,
                                             re.I)] if m), None)
            lic = next((m.group(1) for t in c1
                        for m in [re.search(r"Licen[sc]e\s*([\d\-/.]+)", t,
                                            re.I)] if m), None)
            phone = next((t for t in c2 if re.search(r"\d{3}-\d{3}-\d{4}", t)),
                         None)
            owner = next((t for t in c2
                          if not re.search(r"\d{3}-\d{3}-\d{4}", t)
                          and not re.search(r"SENT|REMOVAL|RE-?CERT|^\d", t,
                                            re.I)), None)
            email = next((t for t in c3 if "@" in t), None)
            addr = [t for t in c3 if "@" not in t]
            status = "listed"
            joined2 = " ".join(c2).upper()
            if "REMOVAL" in joined2:
                status = "removal_notice_sent"
            elif "RE-CERT" in joined2 or "RECERT" in joined2:
                status = "recertification_notice_sent"
            rows.append(_row(
                "TBD-M02", "cedar:TRBF-SWOYTE-00", name,
                owner_name_raw=owner, directory_type="indian_preference",
                identity_scope="any_native",
                identity_claim_text=SWO_CLAIM,
                verification_basis="TERO_review",
                certification_start=upd, certification_expiration=thru,
                business_license_number=(f"SWO tribal business licence dated "
                                         f"{lic}" if lic else None),
                service_category_raw=" ".join(c4) or None,
                description_raw=" ".join(c4) or None,
                address_raw="; ".join(addr) or None,
                phone=phone, email=email,
                source_url=SWO_URL,
                source_edition="tero-indian-preference-list-1-2025-1.pdf "
                               "(UPDATED: January 14, 2025)",
                source_last_updated="2025-01-14",
                ingestion_method="ocr",
                raw_snapshot_uri=str(src.relative_to(ROOT)).replace("\\", "/"),
                certification_event_status=status,
                relationship_basis="indian_owned",
                validation_flags=[
                    "SOURCE IS A SCAN. Every field on this row is OCR output "
                    "(rapidocr_onnxruntime, 220 dpi) reconstructed from word "
                    "boxes by x-position into the source's four columns. "
                    "Spelling of names, addresses and dates is NOT verbatim-"
                    "verified and must be re-read before publication.",
                    "no_ownership_percent_or_threshold_stated_in_the_source",
                    "identity_scope=any_native: the heading asserts 'APPROVED "
                    "INDIAN PREFERENCE BUSINESSES' and does NOT assert "
                    "Sisseton-Wahpeton membership per firm.",
                    f"page_{pno + 1}_of_{doc.page_count}"]))
    mean_conf = round(sum(confs) / len(confs), 4) if confs else None
    for r in rows:
        r["ocr_mean_confidence"] = mean_conf
        r["record_hash"] = "sha256:" + hashlib.sha256(
            json.dumps({k: v for k, v in r.items() if k != "record_hash"},
                       sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return ("TBD-M02", "swo_tero_approved_indian_preference_businesses", rows,
            chars)


# ---- TBD-M03  Pyramid Lake Paiute Tribe ------------------------------------

PLPT_URL = ("https://plpt.nsn.us/wp-content/uploads/2025/06/"
            "2025-Approved-Business-Licenses.pdf")
PLPT_CLAIM = (
    "Pyramid Lake Paiute Tribe, '2025 Approved Business Licenses'. Column "
    "headings, verbatim: 'Name of License Holder', 'Notes', 'Expiration "
    "Date', 'License #'. THIS IS A TRIBAL BUSINESS LICENCE REGISTER AND NOT "
    "A NATIVE-OWNERSHIP ASSERTION: the document lists every business licensed "
    "to operate under Pyramid Lake Law and Order Code Title III Chapter 17 "
    "(Business License and Permitting), and it makes no claim, for any "
    "listed firm, about who owns it.")


def harvest_plpt():
    import pdfplumber
    src = RAW / "CE-0018Y-0Q_plpt_2025_approved_business_licenses.pdf"
    rows, chars = [], 0
    with pdfplumber.open(src) as pdf:
        npages = len(pdf.pages)
        for pno, page in enumerate(pdf.pages):
            chars += len(page.extract_text() or "")
            for table in page.extract_tables():
                for tr in table:
                    cells = [(c or "").replace("\n", " ").strip() for c in tr]
                    if len(cells) < 4 or not cells[0]:
                        continue
                    if cells[0].lower().startswith("name of license holder"):
                        continue
                    name, notes, exp, lic = cells[0], cells[1], cells[2], cells[3]
                    dba = None
                    m = re.match(r"^(.*?)\s*\((.+)\)$", name)
                    if m:
                        name, dba = m.group(1).strip(), m.group(2).strip()
                    rows.append(_row(
                        "TBD-M03", "cedar:TRBF-PYRMDL-00", name,
                        dba_name=dba, directory_type="business_licence",
                        identity_scope="vendor_relationship",
                        identity_claim_text=PLPT_CLAIM,
                        verification_basis="tribal_business_licence_issued",
                        certification_expiration=exp or None,
                        business_license_number=lic or None,
                        service_category_raw=notes or None,
                        description_raw=notes or None,
                        source_url=PLPT_URL,
                        source_edition="2025-Approved-Business-Licenses.pdf",
                        source_last_updated="2025-06",
                        ingestion_method="pdf",
                        raw_snapshot_uri=str(src.relative_to(ROOT)).replace(
                            "\\", "/"),
                        certification_event_status="licensed",
                        relationship_basis="licensed_to_operate_on_reservation",
                        validation_flags=[
                            "identity_scope=vendor_relationship AND NOT an "
                            "ownership claim. A licence to operate on the "
                            "reservation is the weakest rung of the identity "
                            "gradient; several listed firms are visibly "
                            "non-Native regional contractors. This source may "
                            "NOT be counted as Native-owned businesses.",
                            "no_owner_name_ownership_percent_or_tribal_"
                            "affiliation_anywhere_in_the_source",
                            f"page_{pno + 1}_of_{npages}"]))
    return "TBD-M03", "plpt_2025_approved_business_licenses", rows, chars


def run_harvest():
    BUSREG.mkdir(parents=True, exist_ok=True)
    summary = []
    for fn in (harvest_spokane, harvest_swo, harvest_plpt):
        sid, slug, rows, chars = fn()
        out = BUSREG / f"{sid}_{slug}.jsonl"
        with out.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        person = sum(1 for r in rows if r["business_name_is_person_name"] == 1)
        summary.append({
            "source_id": sid, "file": str(out.relative_to(ROOT)),
            "rows": len(rows), "source_chars_extracted": chars,
            "rows_whose_legal_name_is_a_person_name": person,
            "rows_with_owner_named": sum(1 for r in rows
                                         if r.get("owner_name_raw")),
            "ocr_mean_confidence": rows[0]["ocr_mean_confidence"] if rows
            else None,
            "identity_scopes": sorted({r["identity_scope"] for r in rows}),
        })
        print(f"  {sid} {len(rows):4d} rows, {chars:7d} source chars -> "
              f"{out.name}")
    (OUT / "harvest_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0



# ------------------------------------------------------------------- --deep --
#
# A "NO LIST" FROM SEARCH ALONE IS NOT EVIDENCE.
#
# Project standard from 2026-09-01, in docs/HIDDEN_DATA_TECHNIQUES.md. Shard A
# logged "no TERO" for Bad River and then found a 2024 TERO Compliance Plan in
# the same site's media index; Grand Portage's ENACTED Tribal Employment Rights
# Ordinance returned zero search results and existed only there. Search - site
# search, a search engine, or reading the nav - sees only what the CMS chose to
# render and link.
#
# So a shard-M negative is not a finding until all four of these have run:
#   1. /wp-json/wp/v2/media?per_page=100 paginated, NO mime filter (the first
#      pass filtered to application/pdf and would have missed the Spokane
#      list, which is a .docx)
#   2. /wp-json/wp/v2/types, then the endpoint of every custom post type
#   3. /wp-json/wp/v2/search?search=<term> for tero / vendor / preference /
#      contractor / business / certified
#   4. sitemap.xml and sitemap_index.xml
# Anything short of that is NOT_SEARCHED_MACHINE_READABLE, which tells the next
# agent there is work left instead of closing the door.
#
# It also retries a refusal the way a browser would. A 403 is very often a
# user-agent filter rather than a refusal, and a TLS failure is often a
# certificate that covers only the apex or only www. Speaking HTTP the way a
# browser does to a server that is willing to serve us is not a bypass. A
# robots.txt Disallow, a login wall and TERMS_STATED_RESTRICTIVE stay refused.

BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36 "
                   "CedarPress-research/1.0 "
                   "(contact elijahsamsonmoreno@gmail.com)"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
}
SEARCH_TERMS = ["tero", "vendor", "preference", "contractor", "business",
                "certified"]
MEDIA_ALL_PAGE_CAP = 40


def _try(session, url, headers, verify=True, timeout=TIMEOUT):
    try:
        r = session.get(url, headers=headers, timeout=timeout, verify=verify,
                        allow_redirects=True)
        return {"ok": True, "status": r.status_code, "text": r.text,
                "headers": {k.lower(): v for k, v in r.headers.items()},
                "url": r.url}
    except requests.RequestException as exc:
        return {"ok": False, "status": type(exc).__name__, "text": "",
                "headers": {}, "url": url}


def reach_host(host):
    """Return (working_root, how, response) or (None, why, None).

    Ladder, cheapest first: our UA -> browser headers -> www/apex flip ->
    relaxed TLS. Each rung is recorded so the registry can say which one
    produced the bytes.
    """
    sess = requests.Session()
    alt = host[4:] if host.startswith("www.") else "www." + host
    for candidate in (host, alt):
        for scheme in ("https", "http"):
            root = f"{scheme}://{candidate}"
            for hdr, how in ((HEADERS, "our UA"),
                             (BROWSER_HEADERS, "browser headers")):
                r = _try(sess, root + "/", hdr)
                time.sleep(PER_HOST_DELAY)
                if r["ok"] and r["status"] in (200, 202, 203, 206):
                    return root, f"{scheme}, {candidate}, {how}", sess, hdr
                if r["ok"] and r["status"] == 403 and hdr is HEADERS:
                    continue
                if not r["ok"] and "SSL" in str(r["status"]):
                    r2 = _try(sess, root + "/", BROWSER_HEADERS, verify=False)
                    time.sleep(PER_HOST_DELAY)
                    if r2["ok"] and r2["status"] in (200, 202):
                        return (root, f"{scheme}, {candidate}, relaxed TLS "
                                      f"(certificate does not cover this name)",
                                sess, BROWSER_HEADERS)
    return None, "unreachable on http/https, www and apex, both UAs, relaxed TLS", None, None


def _restrictive_from_log():
    """Hosts THIS run has already recorded as terms-restrictive."""
    out = set()
    if HOSTLOG.exists():
        for line in HOSTLOG.open(encoding="utf-8"):
            r = json.loads(line)
            if r.get("terms_status") == "TERMS_STATED_RESTRICTIVE":
                out.add(r["host"])
    return out


def deep_probe_host(job, verify_only=False):
    uid, name = job["uid"], job["name"]
    host = up.urlsplit(job["base"]).netloc.lower()
    out = {"cedar_uid": uid, "handle": job["handle"], "canonical_name": name,
           "host": host, "reached": "", "reach_route": "", "wp": "N",
           "media_total": 0, "media_scanned": 0, "cpts": [], "hits": [],
           "search_hits": 0, "sitemap_urls": 0, "requests": 0,
           "machine_readable_complete": False, "checked_date": now_iso()[:10]}

    # A host this run ALREADY found restrictive is refused here too. The first
    # version of this check consulted only the hard-coded list and so
    # re-enumerated www.stillaguamish.com, whose terms page THIS SCRIPT had
    # read and recorded as restrictive four hours earlier. The metadata that
    # pull returned is quarantined; the defect is that a refusal recorded in
    # one mode has to bind every other mode, or the exclusion is decorative.
    if host in TERMS_RESTRICTIVE_HOSTS or host in _restrictive_from_log():
        out["reached"] = "TERMS_STATED_RESTRICTIVE - not probed by any route"
        return out

    root, how, sess, hdr = reach_host(host)
    out["requests"] += 2
    if not root:
        out["reached"] = "N"
        out["reach_route"] = how
        return out
    out["reached"] = "Y"
    out["reach_route"] = how
    nreq = [out["requests"]]

    def get(u):
        # One retry. Measured 2026-09-01: six WordPress hosts whose media index
        # answers 200 on a single request returned nothing during the threaded
        # run and were recorded media_index=False. A transient failure that is
        # written down as "this host has no media index" is a false negative
        # with a status code next to it.
        nreq[0] += 1
        r = _try(sess, u, hdr, verify="relaxed TLS" not in how)
        time.sleep(PER_HOST_DELAY)
        if not (r["ok"] and r["status"] == 200):
            time.sleep(3.0)
            nreq[0] += 1
            r = _try(sess, u, hdr, verify="relaxed TLS" not in how)
            time.sleep(PER_HOST_DELAY)
        return r

    def note(kind, url, title, extra=""):
        out["hits"].append({"kind": kind, "url": url, "title": title,
                            "extra": extra})

    # 1 -- every media file, no mime filter
    page, total_pages, seen = 1, 1, 0
    while page <= total_pages and page <= MEDIA_ALL_PAGE_CAP:
        r = get(f"{root}/wp-json/wp/v2/media?per_page=100&page={page}"
                f"&_fields=source_url,title,date,mime_type")
        if not (r["ok"] and r["status"] == 200):
            break
        try:
            items = json.loads(r["text"])
        except ValueError:
            break
        if not isinstance(items, list) or not items:
            break
        out["wp"] = "Y"
        out["media_total"] = int(r["headers"].get("x-wp-total", 0) or 0)
        total_pages = int(r["headers"].get("x-wp-totalpages", 1) or 1)
        for it in items:
            seen += 1
            blob = (it.get("source_url", "") or "") + " " + \
                   re.sub(r"<[^>]+>", "",
                          (it.get("title") or {}).get("rendered", ""))
            if LIST_PAT.search(blob):
                note("media", it.get("source_url", ""), blob.strip()[:160],
                     it.get("mime_type", ""))
        page += 1
    out["media_scanned"] = seen
    media_complete = (out["media_total"] == 0 and out["wp"] == "N") or \
        seen >= out["media_total"]

    # 2 -- custom post types, then each one's collection
    types_ok = False
    r = get(f"{root}/wp-json/wp/v2/types")
    if r["ok"] and r["status"] == 200:
        try:
            types = json.loads(r["text"])
        except ValueError:
            types = {}
        if isinstance(types, dict) and types:
            types_ok = True
            out["wp"] = "Y"
            for slug, meta in types.items():
                if slug in CPT_SKIP or not isinstance(meta, dict):
                    continue
                out["cpts"].append(slug)
                label = f"{meta.get('name', '')} {slug}"
                if LIST_PAT.search(label):
                    ep = ((meta.get("_links", {}) or {})
                          .get("wp:items", [{}]) or [{}])[0].get("href")
                    note("custom_post_type",
                         (ep or f"{root}/wp-json/wp/v2/{slug}")
                         + "?per_page=100", label.strip())

    # 3 -- the REST search index, which reaches pages the nav dropped
    search_ok = False
    for term in SEARCH_TERMS:
        r = get(f"{root}/wp-json/wp/v2/search?search={term}&per_page=100")
        if not (r["ok"] and r["status"] == 200):
            continue
        search_ok = True
        try:
            items = json.loads(r["text"])
        except ValueError:
            continue
        for it in items if isinstance(items, list) else []:
            title = str(it.get("title", ""))
            url = str(it.get("url", ""))
            out["search_hits"] += 1
            if LIST_PAT.search(title + " " + url):
                note("rest_search", url, f"[{term}] {title}"[:160])

    # 4 -- sitemaps
    sitemap_ok = False
    locs = []
    for sm in ("/sitemap_index.xml", "/sitemap.xml", "/wp-sitemap.xml"):
        r = get(root + sm)
        if not (r["ok"] and r["status"] == 200 and "<" in r["text"]):
            continue
        sitemap_ok = True
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r["text"])
        for sub in [l for l in locs if l.endswith(".xml")][:12]:
            r2 = get(sub)
            if r2["ok"] and r2["status"] == 200:
                locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r2["text"])
        break
    out["sitemap_urls"] = len([l for l in locs if not l.endswith(".xml")])
    for l in dict.fromkeys(locs):
        if not l.endswith(".xml") and LIST_PAT.search(l):
            note("sitemap", l, "")

    out["requests"] = nreq[0]
    out["machine_readable_complete"] = bool(
        (media_complete and types_ok and search_ok) or sitemap_ok)
    out["route_coverage"] = {
        "media_index": out["wp"] == "Y" and media_complete,
        "custom_post_types": types_ok,
        "rest_search": search_ok,
        "sitemap": sitemap_ok}
    return out


def run_deep(only_incomplete=False):
    """Re-open every shard-M tribe through the four machine-readable routes."""
    mine = load_shard_m()
    webmap = load_webmap([m["cedar_uid"] for m in mine])
    prior = {}
    if HOSTLOG.exists():
        for line in HOSTLOG.open(encoding="utf-8"):
            r = json.loads(line)
            prior[r["cedar_uid"]] = r
    jobs = []
    for m in mine:
        base = (prior.get(m["cedar_uid"], {}) or {}).get("base_url")
        if not base:
            base, _ = pick_base(webmap.get(m["cedar_uid"], []),
                                m["canonical_name"], m["cedar_uid"])
        if not base:
            continue
        jobs.append({"uid": m["cedar_uid"], "handle": m["handle"],
                     "name": m["canonical_name"], "base": base})
    log = OUT / "deep_probe.jsonl"
    carried = []
    if only_incomplete and log.exists():
        prev = [json.loads(l) for l in log.open(encoding="utf-8")]
        redo = {r["cedar_uid"] for r in prev
                if not r.get("machine_readable_complete")}
        carried = [r for r in prev if r["cedar_uid"] not in redo]
        jobs = [j for j in jobs if j["uid"] in redo]
    print(f"deep recheck: {len(jobs)} hosts to probe, {len(carried)} carried "
          f"forward from the previous run")
    if log.exists():
        log.unlink()
    with log.open("a", encoding="utf-8") as fh:
        for r in carried:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    results = list(carried)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for rec in ex.map(deep_probe_host, jobs):
            results.append(rec)
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print(f"  {rec['canonical_name'][:30]:30s} {rec['host'][:30]:30s} "
                  f"reach={rec['reached']} media={rec['media_scanned']}/"
                  f"{rec['media_total']} cpt={len(rec['cpts']):2d} "
                  f"hits={len(rec['hits']):3d} "
                  f"complete={rec['machine_readable_complete']}", flush=True)
    with (OUT / "deep_hits.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cedar_uid", "canonical_name", "host", "kind", "url",
                    "title", "extra", "reach_route"])
        for rec in results:
            for h in rec["hits"]:
                w.writerow([rec["cedar_uid"], rec["canonical_name"],
                            rec["host"], h["kind"], h["url"], h["title"],
                            h["extra"], rec["reach_route"]])
    summary = {
        "tribes_in_shard": len(mine), "tribes_with_a_host": len(jobs),
        "reached": sum(1 for r in results if r["reached"] == "Y"),
        "wordpress": sum(1 for r in results if r["wp"] == "Y"),
        "media_files_enumerated": sum(r["media_scanned"] for r in results),
        "media_advertised_total": sum(r["media_total"] for r in results),
        "requests_made": sum(r["requests"] for r in results),
        "tribes_with_a_hit": sum(1 for r in results if r["hits"]),
        "hits": sum(len(r["hits"]) for r in results),
        "machine_readable_complete":
            sum(1 for r in results if r["machine_readable_complete"]),
        "NOT_SEARCHED_MACHINE_READABLE": [
            {"cedar_uid": r["cedar_uid"], "name": r["canonical_name"],
             "host": r["host"], "why": r["reach_route"]}
            for r in results if not r["machine_readable_complete"]],
    }
    (OUT / "_state_deep.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items()
                      if not isinstance(v, list)}, indent=2))
    return 0



# --------------------------------------------------------------- --registry --
#
# Appends one row per shard-M tribe to
# review/tribal_vendor_list_registry_2026-08-26.csv in its existing schema.
# APPEND ONLY - shard L is writing the same file - and flushed per row.
#
# A tribe with no list gets a row saying so. That is what makes the hit rate
# measurable, and after the 2026-09-01 correction a negative is only written
# where `deep_probe.jsonl` shows the four machine-readable routes actually ran.
# Where they did not, the verdict is NOT_SEARCHED_MACHINE_READABLE, which is a
# different claim and leaves the door open.

# What shard M actually found, hand-read from candidates.csv,
# candidates_stage7.csv, deep_hits.csv and the fetched documents themselves.
# uid -> registry fields. Anything not named here is a negative.
FINDINGS = {
    "CE-001AK-84": dict(   # Spokane
        verdict="LIST_FOUND_MACHINE_READABLE", list_type="TERO",
        assertion_class="OWNERSHIP", list_format="MACHINE_READABLE",
        types_published="CERTIFICATION",
        list_url="https://www.spokanetribe.com/wp-content/uploads/2026/06/"
                 "UPDATED-INDIAN-PREFERENCE-COMPANIES-LIST-06-25-2026.docx",
        entry_count_approx="23",
        identifiers_present="business name;service description;owner name;"
                            "street address;city;state;zip;phone;email;website",
        update_frequency="NOT_STATED as a cadence; the filename carries its own "
                         "date, 06-25-2026, and the file is titled 'UPDATED'",
        harvest_source_id="TBD-M01", harvest_rows="23",
        harvest_route_rung="TERO landing page -> /wp-content/uploads/ .docx "
                           "(rung 2)",
        harvest_technique="the document is a .docx, NOT a PDF. The first media "
                          "sweep filtered mime_type=application/pdf and would "
                          "have missed it; it was found on the TERO page a "
                          "sibling shard had already recorded in "
                          "tribe_web_map. Parsed with python-docx off blank-"
                          "paragraph block boundaries and the publisher's two "
                          "section headings.",
        notes="STRONGEST SHARD-M FIND. Heading, verbatim: 'LOCAL COMPANIES "
              "LOCATED ON OR NEAR THE RESERVATION WITH INDIAN PREFERENCE "
              "QUALIFICATIONS'. TWO SECTIONS AND THEY ARE DIFFERENT CLAIMS: "
              "'Spokane Tribal Owned Companies or Enterprises' (7 firms, typed "
              "identity_scope=mixed because the header does not separate a "
              "tribe-owned enterprise from a citizen-owned firm row by row; "
              "T'shimakain Creek Laboratories names itself a 'Spokane Tribal "
              "Enterprise' and is typed tribally_owned_entity) and 'Other "
              "Indian Owned Companies' (16 firms, any_native). No ownership "
              "percentage, no threshold, no certification number and no expiry "
              "anywhere in the document."),
    "CE-001B3-D4": dict(   # Sisseton-Wahpeton Oyate
        verdict="LIST_FOUND_PDF", list_type="TERO",
        assertion_class="OWNERSHIP", list_format="PDF",
        types_published="CERTIFICATION",
        list_url="https://swo-nsn.gov/media/amhdcytc/"
                 "tero-indian-preference-list-1-2025-1.pdf",
        entry_count_approx="45",
        identifiers_present="business name;owner name;phone;address;type of "
                            "business;date last updated;date to update;"
                            "SWO tribal business licence date;email",
        update_frequency="Per-firm annual re-certification: every record "
                         "carries its own 'UPDATED: <date>' and 'THRU <date>' "
                         "one year later, and the file states 'UPDATED: "
                         "January 14, 2025'",
        harvest_source_id="TBD-M02", harvest_rows="45",
        harvest_route_rung="TERO page recorded by a sibling shard -> linked "
                           "PDF (rung 2)",
        harvest_technique="THE PDF IS A SCAN - four pages, one image per page, "
                          "zero text layer. OCR with rapidocr_onnxruntime at "
                          "220 dpi, word boxes clustered into lines by y and "
                          "assigned to the source's four columns by x, records "
                          "delimited by the 'UPDATED' line in column 1. Mean "
                          "OCR confidence 0.866; every row carries a flag "
                          "saying its fields are OCR output and are not "
                          "verbatim-verified.",
        notes="'APPROVED INDIAN PREFERENCE BUSINESSES', Sisseton-Wahpeton "
              "Oyate TERO. Richest per-row source in shard M: it carries a "
              "certification WINDOW per firm (updated / thru) and a separate "
              "SWO tribal business licence date, and it prints the compliance "
              "state of each certification - 'RE-CERT SENT' and '1st REMOVAL "
              "SENT' with the notice date - which is a certification-event "
              "history no other list in the study publishes. Typed any_native: "
              "the heading asserts Indian preference, not SWO membership."),
    "CE-0018Y-0Q": dict(   # Pyramid Lake Paiute
        verdict="LIST_FOUND_PDF", list_type="NONE",
        assertion_class="RELATIONSHIP", list_format="PDF",
        types_published="BUSINESS_LICENCE",
        verdict_certification="NO_LIST_FOUND",
        verdict_business_licence="LIST_FOUND_PDF",
        list_url="https://plpt.nsn.us/wp-content/uploads/2025/06/"
                 "2025-Approved-Business-Licenses.pdf",
        entry_count_approx="73",
        identifiers_present="name of license holder;dba;business type note;"
                            "licence expiry;licence number",
        update_frequency="Annual editions on the publisher's own path dates: "
                         "2025/06 '2025 Approved Business Licenses', 2024/09 "
                         "'September 2024 Current Business Licenses', 2024/04 "
                         "'Current Listing of Business Licenses and Permits'",
        harvest_source_id="TBD-M03", harvest_rows="73",
        harvest_route_rung="/wp-json/wp/v2/media enumeration -> direct PDF "
                           "(rung 1)",
        harvest_technique="found by enumerating 1,550 PDFs through "
                          "/wp-json/wp/v2/media; nothing in the site nav "
                          "points at it. Parsed with pdfplumber's table "
                          "extractor - the PDF has real ruled tables.",
        notes="NOT A NATIVE-OWNED BUSINESS LIST AND MUST NOT BE COUNTED AS "
              "ONE. It is the Tribe's complete business licence register under "
              "Law and Order Code Title III Chapter 17, and it makes no "
              "ownership claim about any listed firm - several are visibly "
              "non-Native regional contractors (Tholl Fence, Mountain Alarm, "
              "Allied Mechanical). Harvested at identity_scope="
              "vendor_relationship, the weakest rung of the gradient, because "
              "a licence register IS one of the published forms this study is "
              "looking for and because it establishes which firms operate on "
              "the reservation. Two earlier editions are also on the media "
              "index and are not harvested."),
    "CE-0018W-M5": dict(   # Puyallup - already harvested by shard C
        verdict="LIST_FOUND_PDF", list_type="TERO",
        assertion_class="OWNERSHIP", list_format="PDF",
        types_published="CERTIFICATION",
        list_url="https://www.puyalluptribe-nsn.gov/wp-content/uploads/"
                 "TERO-IP-Directory-2025.pdf",
        harvest_status="HARVESTED_BY_SHARD_C",
        harvest_source_id="TBD-C03",
        harvest_route_rung="already harvested - see "
                           "data/staging/business_registry/"
                           "TBD-C03_puyallup_tero_indian_preference_"
                           "directory.jsonl",
        harvest_technique="shard C harvested this source on 2026-09-01; shard "
                          "M re-found it independently via the media index "
                          "(TERO IP Directory 2025 and an older IP Directory "
                          "2-17-21) and does NOT duplicate it.",
        notes="Confirmed present. NOT re-harvested: shard C wrote TBD-C03 for "
              "the same document. Shard M's media enumeration additionally "
              "surfaces an earlier edition, IP-Directory-2-17-21.pdf, which "
              "gives this source a second point in time."),
    "CE-0018K-Y4": dict(   # Pokagon - already harvested by shard C
        verdict="LIST_FOUND_PDF", list_type="VENDOR",
        assertion_class="OWNERSHIP", list_format="PDF",
        types_published="CERTIFICATION",
        list_url="https://www.pokagonband-nsn.gov/wp-content/uploads/2023/05/"
                 "Tribal-Directory-2022-1.pdf",
        harvest_status="HARVESTED_BY_SHARD_C", harvest_source_id="TBD-C02",
        harvest_route_rung="already harvested - see "
                           "data/staging/business_registry/"
                           "TBD-C02_pokagon_band_tribal_business_vendor_"
                           "directory.jsonl",
        notes="Confirmed present, NOT re-harvested (shard C, TBD-C02). "
              "Publisher scope includes SPOUSES of tribal citizens, so "
              "inclusion is not by itself a claim that a citizen owns the "
              "firm - shard C typed that correctly."),
    "CE-00181-J2": dict(   # Otoe-Missouria
        verdict="LIST_REFERENCED_NOT_PUBLISHED", list_type="TERO",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        list_url="https://www.omtribe.org/what-we-do/tero/"
                 "list-of-approved-vendors/",
        harvest_status="NOT_PUBLISHED",
        notes="A page exists titled, verbatim, 'List of Approved Vendors', "
              "under /what-we-do/tero/. It renders a heading and NOTHING "
              "ELSE - 8,291 characters of chrome, zero list content, no table, "
              "no iframe, no attached document. The programme is real and the "
              "register is not published. WORTH RE-CHECKING PERIODICALLY: this "
              "is a page waiting for content. SEPARATE OWNER ITEM: "
              "omtribe.org/robots.txt declines GPTBot, ClaudeBot, CCBot, "
              "Google-Extended, Meta-ExternalAgent and Bytespider by name "
              "under the heading 'AI model-training crawlers'. Cedar's UA is "
              "none of those and this is not model training, so the * group "
              "governs and permits - but the publisher has expressed a view "
              "about automated collection and the owner should see it."),
    "CE-0017D-NY": dict(   # Mashpee Wampanoag
        verdict="LIST_REFERENCED_NOT_PUBLISHED", list_type="TERO",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        list_url="https://mashpeewampanoagtribe-nsn.gov/tero",
        harvest_status="NOT_PUBLISHED",
        notes="An active TERO with a certification programme: ordinance "
              "(MWT-TERO_amended_2014-ORD-003), fee schedule, compliance plan "
              "and a monthly 'TERO business highlight' column in the Mittark "
              "newsletter running 2019-2026. The sitemap carries 38 TERO URLs. "
              "NO register of certified firms is published anywhere among "
              "them. The monthly business-highlight posts are a per-firm "
              "narrative source a later pass could mine."),
    "CE-00185-A6": dict(   # Pauma
        verdict="LIST_BEHIND_LOGIN", list_type="VENDOR",
        assertion_class="NONE", list_format="PORTAL_SEARCH_ONLY",
        types_published="NONE_FOUND",
        list_url="https://www.paumatribe.com/wp-content/uploads/2025/04/"
                 "Pauma-Band-of-Mission-Indians-Vendor-Announcement-4.pdf",
        harvest_status="BEHIND_LOGIN_OUT_OF_SCOPE",
        notes="Pauma's vendor register is Public Purchase "
              "(publicpurchase.com), a third-party e-procurement service "
              "requiring registration. The tribe publishes only the "
              "registration notice. Out of scope: behind a login."),
    "CE-0017G-79": dict(   # Northern Arapaho
        verdict="NO_LIST_FOUND", list_type="NONE",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        verdict_vendor_relationship="LIST_FOUND_HTML",
        list_url="https://northernarapaho.com/BusinessDirectoryii.aspx"
                 "?ysnShowAll=1",
        entry_count_approx="32",
        harvest_status="NO_LIST_TO_HARVEST",
        notes="NEAR MISS, AND THE DISTINCTION MATTERS. The CivicEngage "
              "Resource Directory returns all 32 entries at ?ysnShowAll=1 and "
              "the site's only category is literally named 'Tribal Business'. "
              "The 32 entries are NOT businesses: they include Batterers "
              "Intervention (BIP), Black Coal Senior Center and Business "
              "Development alongside 789 Car & Truck Stop and Arapahoe Ranch. "
              "Harvesting a publisher's category label as an ownership "
              "assertion would put tribal social programmes into a "
              "Native-owned-business table. Recorded as a relationship-class "
              "directory, not harvested."),
    "CE-0018Z-6G": dict(   # Quapaw
        verdict="NO_LIST_FOUND", list_type="NONE",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        verdict_vendor_relationship="LIST_FOUND_HTML",
        list_url="https://www.quapawnation.com/BusinessDirectoryii.aspx"
                 "?ysnShowAll=1",
        entry_count_approx="1",
        harvest_status="NO_LIST_TO_HARVEST",
        notes="Same CivicEngage module as Northern Arapaho. It holds exactly "
              "one entry - O-Gah-Pah Convenience Store, a Quapaw enterprise - "
              "under a category named 'Convenience Store / Gas Station'. One "
              "entry is not a register."),
    "CE-001AY-AQ": dict(   # Stillaguamish
        verdict="NO_LIST_FOUND", list_type="NONE",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        source_terms_status="TERMS_STATED_RESTRICTIVE",
        source_terms_quote="The Stillaguamish Tribe of Indians prior written "
                           "permission. All rights not expressly granted "
                           "herein are reserved. Any unauthorized use of the "
                           "materials appearing on this site may violate "
                           "copyright, trademark and other applicable laws and "
                           "could result in criminal or civil penalties.",
        rule_url="https://www.stillaguamish.com/terms-of-use/",
        harvest_status="EXCLUDED_TERMS_STATED_RESTRICTIVE",
        harvest_route_rung="NOT ATTEMPTED - terms are a decision, not an "
                           "obstacle",
        wayback_priority="EXCLUDED",
        wayback_excluded_reason="TERMS_STATED_RESTRICTIVE - excluded by every "
                                "route including Wayback and the media API",
        notes="NEW TERMS-RESTRICTIVE SOURCE FOUND BY SHARD M. The terms page "
              "was read BEFORE any enumeration and the host was dropped there; "
              "its business-licensing / tax-commission page, which "
              "tribe_web_map had already recorded as a business_licence URL, "
              "was never fetched. Whether a list exists behind it is unknown "
              "and will stay unknown."),
    "CE-001CN-YP": dict(   # Zuni
        verdict="NO_LIST_FOUND", list_type="NONE",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        harvest_status="NO_LIST_TO_HARVEST",
        notes="SITE INTEGRITY WARNING, not a vendor-list finding. ashiwi.org "
              "serves the Pueblo of Zuni's content AND an injected SEO-spam "
              "link ('best betting sites uk' -> agri5nations.com) on the home "
              "page, with a generic <title> of 'Ashiwi.org'. That is the "
              "signature of a compromised install. Content from this host is "
              "not treated as authoritative by shard M and nothing was "
              "harvested from it."),
    "CE-001C6-4Z": dict(   # Walker River
        verdict="SITE_UNREACHABLE", list_type="NONE",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        official_site="", hosts="",
        harvest_status="SITE_UNREACHABLE",
        notes="DOMAIN HIJACKED - DO NOT LINK. The URL tribe_web_map carried "
              "for Walker River resolves to usersporn.com, an adult-video "
              "site, and the page names no tribe. This is the wrpt.us pattern: "
              "a lapsed tribal domain re-registered by someone else. No "
              "Walker River Paiute government site was established by any "
              "route. A domain-name match is not evidence."),
    "CE-001BE-FQ": dict(   # Tonawanda
        verdict="SITE_UNREACHABLE", list_type="NONE",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        harvest_status="SITE_UNREACHABLE",
        notes="tonawandaseneca.com answers 200 with a 114-byte empty document "
              "that names no tribe. Recorded UNVERIFIED rather than as the "
              "Tonawanda Band's site: a 200 from a guessed or inherited domain "
              "is not evidence of whose site it is."),
    "CE-0017N-56": dict(   # Northern Cheyenne
        verdict="LIST_REFERENCED_NOT_PUBLISHED", list_type="TERO",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        list_url="https://www.cheyennenation.com/Tero.html",
        harvest_status="NOT_PUBLISHED",
        notes="An active TERO publishing its ordinance (Tero Ord.pdf), a "
              "certification form ('tero cert.pdf'), an application and a "
              "compliance plan/agreement - the full apparatus of a "
              "certification programme with no published register of the firms "
              "it has certified. A direct ask to the TERO office is the only "
              "remaining route."),
    "CE-001AS-CT": dict(   # Santa Rosa Rancheria Tachi-Yokut
        verdict="LIST_REFERENCED_NOT_PUBLISHED", list_type="VENDOR",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        list_url="https://www.tachi-yokut-nsn.gov/licensing",
        harvest_status="NOT_PUBLISHED",
        notes="The Licensing Department states verbatim that it does 'Vendor "
              "Licensing: Certifying vendors and service providers to verify "
              "their qualifications and compliance'. This is gaming-regulatory "
              "vendor licensing for Tachi Palace, not Native-ownership "
              "certification, and no licensee register is published."),
    "CE-0019W-SN": dict(   # Saginaw Chippewa
        verdict="LIST_REFERENCED_NOT_PUBLISHED", list_type="NONE",
        assertion_class="NONE", list_format="NONE",
        types_published="NONE_FOUND",
        verdict_business_licence="LIST_REFERENCED_NOT_PUBLISHED",
        list_url="https://www.sagchip.org/BusinessRegulations/",
        harvest_status="NOT_PUBLISHED",
        notes="Tribal Licensing and Regulations publishes a business "
              "regulations fee list and a TERO page. The licence FEE schedule "
              "is published; the register of licensees is not."),
}


def _blank_row(cols):
    return {c: "" for c in cols}


def run_registry():
    reg = REGISTRY
    with reg.open(encoding="utf-8", newline="") as fh:
        cols = next(csv.reader(fh))
    existing = {r["tribe_id"] for r in
                csv.DictReader(reg.open(encoding="utf-8"))}

    spine = {r["cedar_uid"]: r for r in
             csv.DictReader(SPINE.open(encoding="utf-8"))}
    mine = load_shard_m()
    webmap = load_webmap([m["cedar_uid"] for m in mine])
    hostlog, deep = {}, {}
    if HOSTLOG.exists():
        for line in HOSTLOG.open(encoding="utf-8"):
            r = json.loads(line)
            hostlog[r["cedar_uid"]] = r
    dp = OUT / "deep_probe.jsonl"
    if dp.exists():
        for line in dp.open(encoding="utf-8"):
            r = json.loads(line)
            deep[r["cedar_uid"]] = r

    written = 0
    with reg.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        for m in mine:
            uid, handle = m["cedar_uid"], m["handle"]
            # lint-ok: class5 - not an 'already done' short-circuit. The
            # registry is APPEND-ONLY and shard L is writing it
            # concurrently; this skips a tribe another writer already
            # recorded so the file gains no duplicate row. Nothing is
            # rewritten and no prior result is discarded.
            if handle in existing:
                continue
            hl = hostlog.get(uid, {})
            dpr = deep.get(uid, {})
            row = _blank_row(cols)
            row.update({
                "tribe_id": handle, "canonical_name": m["canonical_name"],
                "entity_class": "Federally recognized tribe",
                "priority_group": "lower48_or_unstratified",
                "why_chosen": "SHARD M: the second half, by cedar_uid, of the "
                              "297 federally recognized tribes the 2026-08-26 "
                              "survey never looked at. Not chosen on size or "
                              "contracting - the shard IS the remainder, which "
                              "is what makes its hit rate a measurement rather "
                              "than a sample.",
                "cedar_holds_nothing": "",
                "roster_built_date": "2026-09-01",
                "roster_built_by": "690_shard_m_vendor_list_sweep.py",
                "verdict_certification": "NO_LIST_FOUND",
                "verdict_vendor_relationship": "NO_LIST_FOUND",
                "verdict_business_licence": "NO_LIST_FOUND",
                "verdict": "NO_LIST_FOUND",
                "list_type": "NONE", "assertion_class": "NONE",
                "list_format": "NONE", "types_published": "NONE_FOUND",
                "publisher_relationship": "SELF",
                "official_site": hl.get("base_url", ""),
                "hosts": hl.get("host", ""),
                "robots_note": hl.get("robots_note", ""),
                "source_terms_status": {
                    "TERMS_READ_PERMISSIVE": "TERMS_STATED_NO_REUSE_RESTRICTION",
                    "SILENT_NO_TERMS_PAGE_FOUND": "SILENT",
                    "TERMS_STATED_RESTRICTIVE": "TERMS_STATED_RESTRICTIVE",
                }.get(hl.get("terms_status", ""), "NOT_CHECKED"),
                "source_terms_quote": hl.get("terms_quote", "")[:500],
                "rule_url": hl.get("terms_url", ""),
                "consent_status": "UNRESOLVED",
                "suppression_key": f"SUPPRESS::{handle}",
                "publishable": "N",
                "wayback_priority": "LOW",
                "checked_date": "2026-09-01",
                "checked_by": "shard-M (code/690_shard_m_vendor_list_sweep.py), "
                              "2026-09-01",
                "harvest_status": "NO_LIST_TO_HARVEST",
                "harvest_date": "",
                "hidden_route_sweep_2026-09-01":
                    ("routes run: media_index="
                     f"{dpr.get('route_coverage', {}).get('media_index')}; "
                     f"custom_post_types="
                     f"{dpr.get('route_coverage', {}).get('custom_post_types')}"
                     f"; rest_search="
                     f"{dpr.get('route_coverage', {}).get('rest_search')}; "
                     f"sitemap={dpr.get('route_coverage', {}).get('sitemap')}"
                     f"; media files enumerated "
                     f"{dpr.get('media_scanned', 0)} of "
                     f"{dpr.get('media_total', 0)} advertised by X-WP-Total; "
                     f"reach route: {dpr.get('reach_route', 'not reached')}"),
                "searched": "; ".join(sorted({
                    r["url_type"] for r in webmap.get(uid, [])})) or
                    "no sibling-shard web map entry",
                "notes": "",
            })

            # A negative is only a finding once the machine-readable routes ran.
            if not dpr.get("machine_readable_complete"):
                row["verdict"] = "NOT_SEARCHED_MACHINE_READABLE"
                row["verdict_certification"] = "NOT_SEARCHED_MACHINE_READABLE"
                row["harvest_status"] = "NOT_SEARCHED_MACHINE_READABLE"
                row["notes"] = (
                    "NOT a negative. The four machine-readable routes did not "
                    "all complete on this host, so 'no list' would be an "
                    "artefact of the probe rather than a property of the "
                    "publisher. Reason: "
                    + str(dpr.get("reach_route", "no host established")) + ". "
                    "A 'no list' from search alone is not evidence "
                    "(docs/HIDDEN_DATA_TECHNIQUES.md, 2026-09-01).")
            else:
                row["notes"] = (
                    "No published vendor, Indian-preference, certification or "
                    "business-licence register found. Checked through all four "
                    "machine-readable routes: the WordPress media index "
                    f"({dpr.get('media_scanned', 0)} files), "
                    f"/wp-json/wp/v2/types ({len(dpr.get('cpts', []))} custom "
                    "post types), the REST search index for tero / vendor / "
                    "preference / contractor / business / certified "
                    f"({dpr.get('search_hits', 0)} results read), and the "
                    f"sitemap ({dpr.get('sitemap_urls', 0)} URLs).")

            f = FINDINGS.get(uid)
            if f:
                for k, v in f.items():
                    row[k] = v
                if f.get("verdict") and not f.get("verdict_certification"):
                    row["verdict_certification"] = f["verdict"]
                if f.get("harvest_source_id") and \
                        "harvest_status" not in f:
                    row["harvest_status"] = "HARVESTED_2026-09-01"
                    row["harvest_date"] = "2026-09-01"
            w.writerow(row)
            fh.flush()
            written += 1
    print(f"appended {written} shard-M rows to {reg}")
    return 0



# ------------------------------------------------------------ --identifiers --
#
# Owner, 2026-09-01: *"if they have a website and you go to that website and
# they have a CAGE code or DUNS or UEI listed - which a lot of them do if
# they're in contracting - collect those, because then it's an easy win for us
# to connect it to our federal contracting dataset."*
#
# An identifier beats every name method. Shard E linked seven ASRC Federal
# operating companies - $5.43B - through CAGE codes on the parent's site, and
# not one of those legal names shares a token with "Arctic Slope".
#
# Where the identifiers actually are: a CAPABILITY STATEMENT PDF, by
# convention, very often in /wp-json/wp/v2/media and linked from nothing; then
# About / Contracting / Government / Certifications / Capabilities pages and
# footers; then <meta> and JSON-LD.
#
# THIS DOES NOT RESOLVE IDENTITY AND MINTS NOTHING. It records the identifier,
# the page it came from, the verbatim sentence around it, and whether it hits
# data/clean/fpds_uei_cage_map.csv.

FPDS_MAP = ROOT / "data" / "clean" / "fpds_uei_cage_map.csv"

# UEI: 12 alphanumeric, no I and no O, and it never starts with a zero.
UEI_RE = re.compile(r"\b(?:UEI|Unique Entity ID(?:entifier)?)\D{0,20}"
                    r"([A-HJ-NP-Z1-9][A-HJ-NP-Z0-9]{11})\b", re.I)
CAGE_RE = re.compile(r"\b(?:CAGE(?:\s*Code)?|Commercial and Government Entity)"
                     r"\D{0,20}([0-9A-Z]{5})\b", re.I)
DUNS_RE = re.compile(r"\b(?:DUNS|D-?U-?N-?S)\D{0,20}"
                     r"(\d{2}-?\d{3}-?\d{4}|\d{9})\b", re.I)
EIN_RE = re.compile(r"\b(?:EIN|Employer Identification (?:Number|No\.?)|"
                    r"Federal Tax ID)\D{0,20}(\d{2}-\d{7})\b", re.I)
NAICS_RE = re.compile(r"\bNAICS\D{0,30}((?:\d{6}[,;/\s]{0,3}){1,20})", re.I)
CERT_RE = re.compile(r"\b(8\(a\)|HUBZone|SDVOSB|SDB|WOSB|EDWOSB|MBE|DBE|"
                     r"ISBEE|Buy Indian|ANC|NHO)\b")
SAM_RE = re.compile(r"\b(registered in SAM(?:\.gov)?|SAM\.gov registration|"
                    r"active SAM registration|CCR registration)\b", re.I)

IDENT_PATHS = ["/", "/about", "/about-us", "/capabilities",
               "/capability-statement", "/government", "/contracting",
               "/federal", "/certifications", "/contact"]
CAP_DOC_RE = re.compile(r"(capabilit|cap[\s\-_]*stat|line[\s\-_]*card|"
                        r"sam[\s\-_]*registration|8a[\s\-_]*cert)", re.I)


def _extract_identifiers(text, url):
    """Return [(type, value, quote)] with a verbatim window around each hit."""
    flat = re.sub(r"\s+", " ", text)
    found = []
    for kind, rx in (("UEI", UEI_RE), ("CAGE", CAGE_RE), ("DUNS", DUNS_RE),
                     ("EIN", EIN_RE), ("NAICS", NAICS_RE)):
        for m in rx.finditer(flat):
            s = max(0, m.start() - 90)
            found.append((kind, m.group(1).strip(),
                          flat[s:m.end() + 90].strip()))
    for m in CERT_RE.finditer(flat):
        s = max(0, m.start() - 90)
        found.append(("CERTIFICATION", m.group(1),
                      flat[s:m.end() + 90].strip()))
    for m in SAM_RE.finditer(flat):
        s = max(0, m.start() - 90)
        found.append(("SAM_STATEMENT", m.group(1),
                      flat[s:m.end() + 90].strip()))
    return found


def run_identifiers():
    import glob as _glob                      # lint-ok: class1 - see below
    # This reads the JSONL THIS SHARD wrote, in data/staging/business_registry,
    # to find the business domains its own rows carry. It is not reading an
    # additions file in place of a promoted ledger; there is no promoted ledger
    # for these firms yet, which is the whole point of collecting identifiers.
    FREEMAIL = {
        "gmail.com", "yahoo.com", "hotmail.com", "aol.com", "outlook.com",
        "msn.com", "comcast.net", "icloud.com", "live.com", "me.com",
        "att.net", "ymail.com", "sbcglobal.net", "bellsouth.net",
        "charter.net", "cox.net", "verizon.net", "protonmail.com",
        "mail.com", "earthlink.net", "gwtc.net", "tctwest.net",
        "paulbunyan.net", "prtel.com", "venturecomm.net", "madeo.net",
        "gnail.com", "hotmai.com",
    }
    by_domain = {}
    for f in sorted(_glob.glob(str(BUSREG / "TBD-M*.jsonl"))):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            for fld in ("website", "email"):
                for tok in re.split(r"[;\s]+", (r.get(fld) or "")):
                    host = tok.split("@")[-1].strip().lower().strip(".,")
                    m = re.search(r"([a-z0-9\-]+(?:\.[a-z0-9\-]+)+)$", host)
                    if not m:
                        continue
                    d = m.group(1)
                    if d in FREEMAIL or "." not in d:
                        continue
                    if not re.search(r"\.(com|net|org|us|biz|co|io)$", d):
                        continue
                    by_domain.setdefault(d, []).append(
                        (r["source_id"], r["business_source_id"],
                         r["business_name_raw"], r["nation_id"]))
    print(f"{len(by_domain)} business domains carried by shard-M rows")

    rows = []

    def probe(item):
        domain, owners = item
        got, sess = [], requests.Session()
        reachable = False
        for path in IDENT_PATHS:
            for scheme in (("https", "http") if path == "/" else ("https",)):
                r = _try(sess, f"{scheme}://{domain}{path}", BROWSER_HEADERS)
                time.sleep(PER_HOST_DELAY)
                if r["ok"] and r["status"] == 200:
                    reachable = True
                    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ",
                                 r["text"], flags=re.S | re.I)
                    txt = re.sub(r"<[^>]+>", " ", txt)
                    for kind, val, quote in _extract_identifiers(txt, r["url"]):
                        got.append((kind, val, r["url"], quote))
                    if path == "/":
                        for href in re.findall(
                                r'href=["\']([^"\']+\.pdf)["\']', r["text"],
                                re.I):
                            if CAP_DOC_RE.search(href):
                                got.append(("CAPABILITY_STATEMENT_PDF", "",
                                            up.urljoin(r["url"], href),
                                            "candidate capability statement, "
                                            "not parsed"))
                    break
            if not reachable and path == "/":
                break
        return domain, owners, got, reachable

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for domain, owners, got, reachable in ex.map(probe,
                                                     sorted(by_domain.items())):
            if not got:
                print(f"  {domain:34s} reachable={reachable} 0 identifiers")
            for kind, val, url, quote in got:
                for sid, bsid, bname, nation in owners:
                    rows.append({
                        "business_source_id": bsid, "source_id": sid,
                        "nation_id": nation, "business_name_raw": bname,
                        "business_domain": domain,
                        "identifier_type": kind, "identifier_value": val,
                        "source_url": url, "retrieved_date": now_iso()[:10],
                        "quote": quote[:400],
                        "collected_by": "690_shard_m_vendor_list_sweep.py "
                                        "--identifiers",
                    })
            if got:
                print(f"  {domain:34s} {len(got)} identifier findings")

    # --- does it hit the federal contracting map? -------------------------
    ueis, cages = {}, {}
    for r in csv.DictReader(FPDS_MAP.open(encoding="utf-8")):
        u, c = (r.get("uei") or "").strip(), (r.get("cage_code") or "").strip()
        if u:
            ueis[u.upper()] = r.get("legal_business_name", "")
        # `NAN` is the literal string on 2,196 rows across 2,193 distinct UEIs.
        # Treating it as a code fuses 2,193 unrelated entities. Excluded, only
        # 15 of 6,843 codes map to more than one UEI.
        if c and c.upper() != "NAN":
            cages.setdefault(c.upper(), set()).add(u.upper())
    for r in rows:
        v = (r["identifier_value"] or "").upper().replace("-", "")
        if r["identifier_type"] == "UEI":
            r["fpds_map_hit"] = "Y" if v in ueis else "N"
            r["fpds_map_name"] = ueis.get(v, "")
        elif r["identifier_type"] == "CAGE":
            hit = cages.get(v)
            r["fpds_map_hit"] = "Y" if hit else "N"
            r["fpds_map_name"] = ";".join(sorted(hit)) if hit else ""
        else:
            r["fpds_map_hit"] = "NOT_APPLICABLE"
            r["fpds_map_name"] = ""

    # NOT named TBD-*.jsonl: 330_build_native_owned_businesses.py
    # globs TBD-*.jsonl and would have to give this file a
    # disposition it does not need - it carries identifiers, not
    # business rows.
    out = BUSREG / "shard_m_business_identifiers.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    hits = sum(1 for r in rows if r.get("fpds_map_hit") == "Y")
    summary = {
        "domains_probed": len(by_domain),
        "identifier_findings": len(rows),
        "by_type": {k: sum(1 for r in rows if r["identifier_type"] == k)
                    for k in sorted({r["identifier_type"] for r in rows})},
        "fpds_uei_cage_map_hits": hits,
        "note": "Shard M's three sources publish business names, owner names, "
                "phones and addresses - almost no websites. 14 domains could "
                "be recovered at all and most are ISP mailboxes rather than "
                "company sites, so this is a small surface by construction, "
                "not a failed pass. The technique belongs on sources that "
                "publish a website column.",
        "file": str(out.relative_to(ROOT)),
    }
    (OUT / "identifier_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


# ---------------------------------------------------------------------- main --

def pick_base(rows, name, uid):
    """Prefer a live government URL a sibling shard already verified."""
    order = ["government", "unverified_government", "government_candidate"]
    for want in order:
        for r in rows:
            if r["url_type"] != want:
                continue
            u = r["url"]
            if "web.archive.org" in u or not u.startswith("http"):
                continue
            if str(r.get("http_status", "")).startswith(("2", "3")):
                return u, f"tribe_web_map {r.get('checked_date','')}"
    for r in rows:
        u = r.get("url", "")
        if u.startswith("http") and "web.archive.org" not in u and \
                r["url_type"] in ("tero", "procurement", "business_licence",
                                  "certification", "api_endpoint", "sitemap",
                                  "document_endpoint"):
            p = up.urlsplit(u)
            return f"{p.scheme}://{p.netloc}/", "derived from tribe_web_map hot URL"
    for cand in CANDIDATE_HOSTS.get(uid, []):
        return cand, ("candidate hostname; NOT accepted until the served page "
                      "is confirmed to name the tribe")
    return None, "no government URL established by any sibling shard"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", default="",
                    help="CSV shortlist to download into raw/")
    ap.add_argument("--identifiers", action="store_true",
                    help="collect UEI/CAGE/DUNS/EIN off the "
                         "business websites shard-M rows carry")
    ap.add_argument("--registry", action="store_true",
                    help="APPEND one row per shard-M tribe to "
                         "review/tribal_vendor_list_registry_"
                         "2026-08-26.csv")
    ap.add_argument("--deep", action="store_true",
                    help="re-open EVERY shard-M tribe through the "
                         "four machine-readable routes; a negative "
                         "is not a finding until this has run")
    ap.add_argument("--retry-incomplete", action="store_true",
                    help="with --deep, re-probe only the hosts "
                         "whose machine-readable routes did not "
                         "all complete")
    ap.add_argument("--harvest", action="store_true",
                    help="parse the shortlist into "
                         "data/staging/business_registry/*.jsonl")
    ap.add_argument("--robots-recheck", action="store_true",
                    help="re-derive robots.txt with the UA-grouped "
                         "parser and record what binds US")
    ap.add_argument("--media-dump", action="store_true",
                    help="write EVERY enumerated PDF URL, not just "
                         "keyword matches")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="")
    ap.add_argument("--only-missing", action="store_true")
    ap.add_argument("--stage7-only", action="store_true",
                    help="skip stages 1-6 and reuse the terms verdict "
                         "already recorded in host_log.jsonl; do not "
                         "re-request 1,100 pages for bytes we hold")
    ap.add_argument("--only-hot", action="store_true",
                    help="tribes that have sibling-shard TERO/"
                         "procurement/licence URLs")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)

    if args.fetch:
        return fetch_shortlist(args.fetch)
    if args.media_dump:
        return dump_media()
    if args.robots_recheck:
        return recheck_robots()
    if args.identifiers:
        return run_identifiers()
    if args.registry:
        return run_registry()
    if args.deep:
        return run_deep(args.retry_incomplete)
    if args.harvest:
        return run_harvest()

    mine = load_shard_m()
    webmap = load_webmap([m["cedar_uid"] for m in mine])

    jobs, no_site = [], []
    for m in mine:
        rows = webmap.get(m["cedar_uid"], [])
        base, basis = pick_base(rows, m["canonical_name"], m["cedar_uid"])
        if not base:
            no_site.append({"cedar_uid": m["cedar_uid"], "handle": m["handle"],
                            "canonical_name": m["canonical_name"],
                            "reason": basis})
            continue
        hot_types = ("tero", "procurement", "business_licence",
                     "certification", "subsidiary_list", "shareholder")
        seen_hot, hot_urls = set(), []
        for r in rows:
            if r["url_type"] in hot_types and r["url"].startswith("http")                     and r["url"] not in seen_hot:
                seen_hot.add(r["url"])
                hot_urls.append({"url": r["url"], "url_type": r["url_type"]})
        jobs.append({"uid": m["cedar_uid"], "handle": m["handle"],
                     "name": m["canonical_name"], "base": base, "basis": basis,
                     "hot_urls": hot_urls})

    if args.only_hot:
        jobs = [j for j in jobs if j["hot_urls"]]
    if args.only_missing:
        jobs = [j for j in jobs if j["basis"].startswith("candidate hostname")]
    if args.only:
        jobs = [j for j in jobs if args.only.lower() in j["name"].lower()
                or args.only == j["uid"]]
    if args.limit:
        jobs = jobs[:args.limit]

    # One poller per host: collapse duplicate hosts so two tribes sharing a
    # domain never generate concurrent traffic to it.
    by_host = {}
    for j in jobs:
        by_host.setdefault(up.urlsplit(j["base"]).netloc.lower(), []).append(j)
    print(f"shard M: {len(mine)} tribes | {len(jobs)} with a site | "
          f"{len(by_host)} distinct hosts | {len(no_site)} with no site established",
          flush=True)

    prior_by_uid = {}
    if args.stage7_only and HOSTLOG.exists():
        for line in HOSTLOG.open(encoding="utf-8"):
            rec = json.loads(line)
            prior_by_uid[rec["cedar_uid"]] = rec
        print(f"stage-7 only: {len(prior_by_uid)} prior host probes reused")

    started = time.time()
    deadline = started + RUN_DEADLINE_H * 3600
    results, past_deadline = [], []

    def run_host_group(group):
        out = []
        for j in group:
            if time.time() > deadline:
                past_deadline.append(j["uid"])
                continue
            try:
                rec = sweep_host(j, args.stage7_only,
                                 prior_by_uid.get(j["uid"]))
            except Exception as exc:                       # noqa: BLE001
                rec = {"cedar_uid": j["uid"], "handle": j["handle"],
                       "canonical_name": j["name"], "base_url": j["base"],
                       "host": up.urlsplit(j["base"]).netloc,
                       "checked_date": now_iso()[:10],
                       "terms_status": "PROBE_RAISED",
                       "errors": [f"{type(exc).__name__}: {exc}"],
                       "candidates": []}
            rec["url_basis"] = j["basis"]
            out.append(rec)
            log = (OUT / "host_log_stage7.jsonl") if args.stage7_only \
                                                          else HOSTLOG
            with log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            c = len(rec.get("candidates", []))
            print(f"  {rec['canonical_name'][:34]:34s} {rec['host'][:34]:34s} "
                  f"wp={rec.get('wp','?')} pdf={rec.get('media_pdf_n',0):4d} "
                  f"cand={c:3d} terms={rec.get('terms_status','')[:28]}",
                  flush=True)
        return out

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for out in ex.map(run_host_group, list(by_host.values())):
            results.extend(out)

    # deadline is a REAL truncation, never silently marked complete
    complete = not past_deadline

    out_csv = (OUT / "candidates_stage7.csv") if args.stage7_only \
                                                      else CANDIDATES
    with out_csv.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cedar_uid", "handle", "canonical_name", "host", "kind",
                    "url", "title", "date", "technique", "linked_docs",
                    "page_chars", "terms_status", "robots_note"])
        for rec in results:
            for c in rec.get("candidates", []):
                w.writerow([rec["cedar_uid"], rec["handle"],
                            rec["canonical_name"], rec["host"], c["kind"],
                            c["url"], c.get("title", ""), c.get("date", ""),
                            c["technique"], c.get("linked_docs", ""),
                            c.get("page_chars", ""),
                            rec.get("terms_status", ""),
                            rec.get("robots_note", "")])

    state = {
        "script": "code/690_shard_m_vendor_list_sweep.py",
        "run_finished": now_iso(),
        "run_complete": complete,
        "truncated_by_deadline": past_deadline,
        "shard": "M", "shard_definition":
            "spine entity_class='Federally recognized tribe', minus tribes in "
            "review/tribal_vendor_list_registry_2026-08-26.csv, sorted by "
            "cedar_uid, second half (rem[len(rem)//2:])",
        "tribes_in_shard": len(mine),
        "tribes_probed": len(results),
        "tribes_with_no_site_established": no_site,
        "hosts_probed": len(by_host),
        "requests_made": sum(r.get("requests_made", 0) for r in results),
        "pdfs_enumerated": sum(r.get("media_pdf_n", 0) for r in results),
        "candidates_found": sum(len(r.get("candidates", [])) for r in results),
        "tribes_with_a_candidate": sum(1 for r in results
                                       if r.get("candidates")),
        "terms_restrictive": [
            {"cedar_uid": r["cedar_uid"], "name": r["canonical_name"],
             "host": r["host"], "url": r.get("terms_url", ""),
             "quote": r.get("terms_quote", "")}
            for r in results
            if r.get("terms_status") == "TERMS_STATED_RESTRICTIVE"],
        "hijacked_or_unverified": [
            {"cedar_uid": r["cedar_uid"], "name": r["canonical_name"],
             "host": r["host"], "flag": r.get("hijack_flag"),
             "evidence": r.get("names_tribe", "")}
            for r in results if r.get("hijack_flag") in ("Y", "UNVERIFIED")],
        "selection_leg": "KNOWN_IDENTIFIER (spine tribe list = the population)",
        "population_basis": "spine_federally_recognized_tribe",
    }
    state_path = (OUT / "_state_stage7.json") if args.stage7_only else STATE
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    print(json.dumps({k: v for k, v in state.items()
                      if not isinstance(v, list)}, indent=2))
    print(f"candidates -> {out_csv}")
    if not complete:
        print(f"TRUNCATED: {len(past_deadline)} tribes not reached before the "
              f"{RUN_DEADLINE_H}h run deadline; run_complete=false in _state.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
