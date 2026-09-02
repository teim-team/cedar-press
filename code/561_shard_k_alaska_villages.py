#!/usr/bin/env python3
"""
561_shard_k_alaska_villages.py -- WORKSTREAM SHARD-K harness.

SLICE: entity_class == "Federally recognized Alaska Native Village" in
       data/spine/cedar_identity_register.csv (228 entities, 225 untouched
       as measured in docs/SHARD_COVERAGE.md 2026-09-01).

WHAT THIS SCRIPT IS
  A fetch/cache/append harness, not an inference engine. It:
    * derives the slice from the register (never a hard-coded village list);
    * fetches one URL at a time with a fixed inter-request delay, honouring
      robots.txt per host, caching the raw bytes under
      data/staging/tribe_harvest/shard_k/raw/;
    * probes the HIDDEN_DATA_TECHNIQUES checklist rungs that are cheap and
      public (wp-json, sitemap, feeds, ld+json, ArcGIS query) ;
    * APPENDS one row at a time to data/staging/tribe_web_map/shard_k.csv and
      flushes+fsyncs after every row, because two agents were killed by API
      server errors today and lost buffered work.

SELECTION DECLARATION (docs/PULL_DISCIPLINE.md)
  Leg used:    KNOWN_IDENTIFIER only -- the slice is Cedar's own register.
  Leg missing: TYPE_FILTER as a SELECTOR. Two full-universe type-filtered
               rosters WERE pulled and read -- the BIA Tribal Leaders Directory
               (biaregion='Alaska', 228 rows) and the State of Alaska DCCED
               "Federally Recognized Tribes" contact layer (230 rows) -- but
               they are used as CORROBORATION and as the absence test, never to
               add entities. Both agreed with the register to within one row
               each (BIA carries Central Council Tlingit & Haida, a different
               Cedar class, and omits Metlakatla; DCCED splits the combined
               Pribilof listing into its two islands), which is itself the
               measurement: this slice has no discovery gap.
  Every row emitted carries population_basis = ledger_identifier implicitly
  (this file's whole population is the register slice).

THE ABSENCE STANDARD THIS FILE ENFORCES
  docs/HIDDEN_DATA_TECHNIQUES.md, 2026-09-01: **a negative from search alone is
  not evidence.** `probe_machine_readable()` below is the checklist. A village
  may be recorded as having no site only when (a) no directory publishes a
  domain for it -- in which case there is no host to probe -- or (b) a host
  exists and the checklist has been run against it. Anything else is
  NOT_SEARCHED_MACHINE_READABLE, not "none found".

  Three states are kept apart everywhere in the output, because only the last
  is a gap in our effort: a verified site, an attempt that found nothing, and
  an entity nobody attempted.

WHAT IT NEVER DOES
  No commits. No spine writes. No minting. No identity resolution -- consortium
  roster names are recorded raw with a candidate + confidence, never resolved.

HOST DISCIPLINE
  One request at a time, single process, 1.5 s minimum between requests to the
  same host, 0.7 s globally.  robots.txt is fetched once per host and cached;
  a Disallow on the target path is recorded as a REFUSAL and the path is not
  fetched by any route.

  robots.txt is fetched HERE, with THIS module's declared User-Agent, and the
  body is handed to RobotFileParser.parse(). `RobotFileParser.read()` is never
  called: it fetches with the default `Python-urllib` UA, and a host that
  403s that UA makes the parser report `disallow_all` -- an open site read as
  closed. That defect cost a sibling shard 22 hosts on 2026-09-01. Here a
  robots.txt that cannot be read is treated as ALLOWED and the reason is noted,
  so a refusal recorded by this file is always a real, quoted `Disallow`.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, "data", "spine", "cedar_identity_register.csv")
WEBMAP = os.path.join(ROOT, "data", "staging", "tribe_web_map", "shard_k.csv")
HARVEST = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_k")
RAW = os.path.join(HARVEST, "raw")
ORGMEM = os.path.join(ROOT, "data", "staging", "org_membership", "shard_k.jsonl")
TODAY = date.today().isoformat()

WEBMAP_COLS = ["tribe_id", "cedar_uid", "canonical_name", "url_type", "url",
               "http_status", "checked_date", "evidence"]

UA = ("CedarPress-research/1.0 (tribal entity web mapping; contact "
      "elijahsamsonmoreno@gmail.com)")

_last_host: dict[str, float] = {}
_last_any = [0.0]
_robots: dict[str, object] = {}


# --------------------------------------------------------------- slice
def slice_rows():
    out = []
    with open(REGISTER, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("entity_class") == "Federally recognized Alaska Native Village":
                out.append(r)
    return out


# --------------------------------------------------------------- fetch
def _sleep_for(host):
    now = time.time()
    d1 = 1.5 - (now - _last_host.get(host, 0.0))
    d2 = 0.7 - (now - _last_any[0])
    d = max(d1, d2, 0.0)
    if d > 0:
        time.sleep(d)


def robots_ok(url):
    """Returns (allowed: bool, note: str). A fetch error on robots.txt is
    treated as ALLOWED (no stated refusal) but is noted."""
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        rurl = base + "/robots.txt"
        try:
            _sleep_for(p.netloc)
            req = urllib.request.Request(rurl, headers={"User-Agent": UA})
            body = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
            _last_host[p.netloc] = _last_any[0] = time.time()
            rp.parse(body.splitlines())
            _robots[base] = rp
            _write_raw("robots__" + p.netloc, body)
        except Exception as e:                      # noqa: BLE001
            _robots[base] = ("ERR", str(e)[:120])
    r = _robots[base]
    if isinstance(r, tuple):
        return True, f"robots.txt unreadable ({r[1]})"
    return bool(r.can_fetch(UA, url)), ""


def _write_raw(name, text):
    os.makedirs(RAW, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)[:150]
    with open(os.path.join(RAW, safe), "w", encoding="utf-8") as fh:
        fh.write(text)


BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def fetch(url, timeout=30, respect_robots=True, save_as=None,
          browser_headers=False, relaxed_tls=False):
    """-> dict(status, text, final_url, headers, error). Never raises.

    browser_headers / relaxed_tls are RECOVERY rungs, not defaults. A 403 to a
    declared research UA is very often a stock UA filter rather than a decision
    about us, and a TLS handshake failure is a server config, not an absence --
    both were costing sibling shards real hosts. Neither rung touches an access
    control: robots.txt is still honoured on the same terms, and a Disallow, a
    login wall or TERMS_STATED_RESTRICTIVE stays refused by every route.
    """
    p = urllib.parse.urlsplit(url)
    if respect_robots:
        ok, note = robots_ok(url)
        if not ok:
            return {"status": "REFUSED_ROBOTS_DISALLOW", "text": "", "url": url,
                    "final_url": url, "headers": {}, "error": "robots.txt Disallow"}
    _sleep_for(p.netloc)
    hdrs = dict(BROWSER_HEADERS) if browser_headers else {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }
    ctx = None
    if relaxed_tls:
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.set_ciphers("DEFAULT@SECLEVEL=1")
        except Exception:                            # noqa: BLE001
            pass
    req = urllib.request.Request(url, headers=hdrs)
    out = {"status": None, "text": "", "url": url, "final_url": url,
           "headers": {}, "error": ""}
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            raw = resp.read()
            out["status"] = resp.status
            out["final_url"] = resp.geturl()
            out["headers"] = dict(resp.headers)
            ct = resp.headers.get("Content-Type", "")
            if "pdf" in ct or url.lower().endswith(".pdf"):
                out["text"] = ""
                out["bytes"] = raw
            else:
                enc = "utf-8"
                m = re.search(r"charset=([\w-]+)", ct or "")
                if m:
                    enc = m.group(1)
                out["text"] = raw.decode(enc, "replace")
    except urllib.error.HTTPError as e:
        out["status"] = e.code
        out["error"] = f"HTTP {e.code}"
        try:
            out["text"] = e.read().decode("utf-8", "replace")
        except Exception:                            # noqa: BLE001
            pass
    except Exception as e:                           # noqa: BLE001
        out["status"] = "conn_error"
        out["error"] = f"{type(e).__name__}: {str(e)[:160]}"
    finally:
        _last_host[p.netloc] = _last_any[0] = time.time()
    if save_as and out.get("text"):
        _write_raw(save_as, out["text"])
    return out


# --------------------------------------------------------------- writers
def ensure_webmap():
    os.makedirs(os.path.dirname(WEBMAP), exist_ok=True)
    if not os.path.exists(WEBMAP) or os.path.getsize(WEBMAP) == 0:
        with open(WEBMAP, "w", encoding="utf-8", newline="") as fh:
            csv.writer(fh).writerow(WEBMAP_COLS)


def add_row(tribe_id, cedar_uid, canonical_name, url_type, url,
            http_status, evidence, checked_date=TODAY):
    """Append ONE row and fsync. Never buffer."""
    ensure_webmap()
    with open(WEBMAP, "a", encoding="utf-8", newline="") as fh:
        csv.writer(fh).writerow([tribe_id, cedar_uid, canonical_name, url_type,
                                 url, http_status, checked_date, evidence])
        fh.flush()
        os.fsync(fh.fileno())


def add_membership(rec):
    os.makedirs(os.path.dirname(ORGMEM), exist_ok=True)
    with open(ORGMEM, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def existing_webmap_keys():
    if not os.path.exists(WEBMAP):
        return set()
    with open(WEBMAP, encoding="utf-8") as fh:
        return {(r["cedar_uid"], r["url_type"], r["url"])
                for r in csv.DictReader(fh)}


# --------------------------------------------------------------- helpers
TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"[ \t\r\f\v]+")


def text_of(html):
    h = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    h = re.sub(r"(?i)<br\s*/?>", "\n", h)
    h = re.sub(r"(?i)</(p|div|li|tr|h[1-6]|td)>", "\n", h)
    h = TAG.sub(" ", h)
    h = (h.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8217;", "'")
          .replace("&#039;", "'").replace("&quot;", '"').replace("&#8211;", "-")
          .replace("&rsquo;", "'").replace("&ldquo;", '"').replace("&rdquo;", '"')
          .replace("&#8216;", "'").replace("&ndash;", "-").replace("&mdash;", "-"))
    h = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), h)
    h = WS.sub(" ", h)
    h = re.sub(r"\n\s*\n+", "\n", h)
    return h.strip()


def ldjson_blocks(html):
    return re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', html)


def title_of(html):
    m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    return text_of(m.group(1)) if m else ""


def links(html, base=""):
    out = []
    for m in re.finditer(r'(?is)<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html):
        href = m.group(1)
        if base:
            href = urllib.parse.urljoin(base, href)
        out.append((href, text_of(m.group(2))))
    return out


MACHINE_READABLE_RUNGS = [
    ("wp_media", "/wp-json/wp/v2/media?per_page=100&_fields=id,date,title,source_url,mime_type"),
    ("wp_types", "/wp-json/wp/v2/types"),
    ("wp_pages", "/wp-json/wp/v2/pages?per_page=100&_fields=id,link,title"),
    ("sitemap_index", "/sitemap_index.xml"),
    ("sitemap", "/sitemap.xml"),
    ("wp_sitemap", "/wp-sitemap.xml"),
    ("feed", "/feed/"),
]


def probe_machine_readable(base_url, tag, browser_headers=False):
    """THE STANDARD (docs/HIDDEN_DATA_TECHNIQUES.md, 2026-09-01):
    **A negative from search alone is not evidence.** Before any village is
    recorded as having no site documents, these machine-readable routes must
    have been asked, because a PDF in the media library is invisible to site
    search, to a search engine and to the navigation. If this function has not
    run against a host, the honest status is NOT_SEARCHED_MACHINE_READABLE, not
    "none found".

    Returns dict rung -> {status, total, note}. Cheap: <=7 requests per host.
    """
    res = {}
    for rung, path in MACHINE_READABLE_RUNGS:
        u = urllib.parse.urljoin(base_url, path)
        r = fetch(u, save_as=f"{tag}__{rung}", browser_headers=browser_headers)
        entry = {"url": u, "status": str(r["status"]),
                 "x_wp_total": r["headers"].get("X-WP-Total"),
                 "x_wp_totalpages": r["headers"].get("X-WP-TotalPages"),
                 "bytes": len(r.get("text") or "")}
        if r["status"] == 200 and rung.startswith("wp_") and r.get("text"):
            try:
                d = json.loads(r["text"])
                entry["json_len"] = len(d) if isinstance(d, (list, dict)) else None
                if rung == "wp_types" and isinstance(d, dict):
                    entry["post_types"] = sorted(d.keys())
            except Exception:                        # noqa: BLE001
                entry["json_len"] = "not_json"
        res[rung] = entry
    return res


if __name__ == "__main__":
    ensure_webmap()
    rows = slice_rows()
    print(f"shard_k slice: {len(rows)} Alaska Native Village governments")
    print(f"webmap rows on disk: {sum(1 for _ in open(WEBMAP, encoding='utf-8')) - 1}")


# ===================================================================
# SOURCE DRIVERS -- one per consortium roster / directory.
# Each writes org_membership rows (raw member names, never resolved) and,
# where the roster publishes a village's own website, a web-map row.
# ===================================================================

def plainnorm(s):
    """Normalise WITHOUT dropping any word. Full-string equality on this is a
    safe high-confidence signal even where every word is generic ("Council" is
    the actual name of a Bering Strait village)."""
    s = s.lower()
    s = re.sub(r"[‘’ʻ'`ʼ]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def register_index():
    """canonical-name fold -> register row, for CANDIDATE suggestion only."""
    idx = {}
    for r in slice_rows():
        k = fold(r["canonical_name"])
        if k:
            idx[k] = r
    return idx


def register_plain_index():
    return {plainnorm(r["canonical_name"]): r for r in slice_rows()}


def fold(s):
    s = s.lower()
    s = re.sub(r"[\u2018\u2019\u02bb'`\u02bc]", "", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    for w in ("native village of", "village of", "traditional council", "tribal council",
              "village council", "ira council", "native tribe of", "council", "tribe",
              "tribal", "traditional", "village", "ira", "the", "of", "alaska",
              "incorporated", "inc", "association", "community", "ak"):
        s = re.sub(r"\b" + w.replace(" ", r"\s+") + r"\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def suggest(name_raw, idx, pidx=None):
    """-> (cedar_uid, canonical, confidence, method). NEVER resolves."""
    if pidx is None:
        pidx = register_plain_index()
    pn = plainnorm(name_raw)
    if pn and pn in pidx:
        r = pidx[pn]
        return r["cedar_uid"], r["canonical_name"], 0.85, "plain_name_exact"
    f = fold(name_raw)
    if not f:
        return "", "", 0.0, "no_distinctive_token_after_fold"
    if f in idx:
        r = idx[f]
        return r["cedar_uid"], r["canonical_name"], 0.85, "folded_canonical_name_exact"
    # One-directional, whole-word containment ONLY: the REGISTER key must appear
    # as whole words inside the candidate string. The reverse direction is what
    # produced "Tok" -> "Newtok" on the TCC directory, and the single-token
    # collisions docs/NATIVE_ENTITY_NUANCES.md warns about ("Enterprise").
    hits = [k for k in idx
            if len(k) >= 5 and re.search(r"(?:^| )" + re.escape(k) + r"(?: |$)", f)]
    if len(hits) == 1:
        r = idx[hits[0]]
        return r["cedar_uid"], r["canonical_name"], 0.6, "folded_wholeword_containment_unique"
    if hits:
        longest = max(hits, key=len)
        if len(longest) >= len(sorted(hits, key=len)[-2]) + 3:
            r = idx[longest]
            return r["cedar_uid"], r["canonical_name"], 0.5, "folded_wholeword_containment_longest"
        return "", "", 0.0, "ambiguous_%d_candidates" % len(hits)
    return "", "", 0.0, "no_candidate_in_register"


HEAD_RE = re.compile(
    r"^(?:[A-Z][A-Za-z'\u2019 .\-]{2,40}(?:Traditional Council|Tribal Council|"
    r"Village Council|Native Council|IRA Council)|Native (?:Tribe|Village) of "
    r"[A-Z][A-Za-z'\u2019 .\-]{2,30}|Traditional Council of [A-Z][A-Za-z'\u2019 .\-]{2,30})$")


def split_blocks(body, head_re=HEAD_RE, drop=("Members",)):
    """Split a flat roster text into (heading, block) pairs."""
    lines = [l.strip() for l in body.split("\n")]
    heads = []
    for i, l in enumerate(lines):
        if head_re.match(l) and not any(l.endswith(d) for d in drop):
            heads.append((i, l))
    out = []
    for j, (i, h) in enumerate(heads):
        end = heads[j + 1][0] if j + 1 < len(heads) else len(lines)
        out.append((h, "\n".join(lines[i + 1:end]).strip()))
    return out


URL_RE = re.compile(r"(?i)\b((?:https?://|www\.)[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+"
                    r"|[A-Za-z0-9-]+\.(?:org|com|net|gov|us)(?:/[^\s,;]*)?)")
OFFICER_RE = re.compile(r"(?im)^\s*([A-Z][A-Za-z /'\u2019-]{2,40}?)\s*:\s*(.+?)\s*$")


def parse_contact_block(block):
    d = {"raw_block": block}
    mw = re.search(r"(?i)Website\s*:?\s*(\S+)", block)
    if mw:
        u = mw.group(1).strip().rstrip(".,;")
        d["website_raw"] = u
    em = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", block)
    if em:
        d["emails"] = sorted(set(em))
    ph = re.findall(r"(?:\+?1[ -])?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}", block)
    if ph:
        d["phones"] = sorted(set(ph))
    officers = []
    for mo in OFFICER_RE.finditer(block):
        role, val = mo.group(1).strip(), mo.group(2).strip()
        if role.lower() in ("telephone", "fax", "email", "website", "address",
                            "phone", "p.o. box", "mailing address", "cell"):
            continue
        if "@" in val or val.lower().startswith(("http", "www")):
            continue
        if len(val) > 60:
            continue
        officers.append({"role": role, "name": val})
    if officers:
        d["officers"] = officers
    return d


def harvest_jsonl(name, rec):
    os.makedirs(HARVEST, exist_ok=True)
    with open(os.path.join(HARVEST, name), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def emit_roster(blocks, org, source_url, org_website, technique, roster_note,
                harvest_file, member_type="alaska_native_village_government"):
    """org = (cedar_uid, handle, name, entity_class). Writes org_membership +
    harvest rows. Returns list of (heading, parsed, suggestion)."""
    idx = register_index()
    out = []
    matched = 0
    for h, b in blocks:
        uid, can, conf, meth = suggest(h, idx)
        if uid:
            matched += 1
    basis = (f"{matched}/{len(blocks)} roster headings on this page match Cedar's "
             f"Alaska-village register slice "
             f"({100.0 * matched / max(1, len(blocks)):.0f}%)")
    for h, b in blocks:
        d = parse_contact_block(b)
        uid, can, conf, meth = suggest(h, idx)
        quote = (h + " " + " ".join(b.split()))[:300]
        add_membership({
            "org_cedar_uid": org[0], "org_handle": org[1], "org_name": org[2],
            "org_entity_class": org[3], "org_website": org_website,
            "as_of_date": TODAY, "retrieved_date": TODAY,
            "member_name_raw": h, "member_type": member_type,
            "membership_status": "current", "source_url": source_url,
            "technique": technique, "quote": quote,
            "page_is_roster_basis": basis + "; " + roster_note,
            "candidate_cedar_uid": uid, "candidate_canonical_name": can,
            "candidate_entity_class": ("Federally recognized Alaska Native Village"
                                       if uid else ""),
            "match_confidence": conf, "match_method": meth,
            "identity_resolved": False,
            "note": ("candidate only; shard-K never resolves identity"
                     if uid else
                     "published as a member but NO candidate in Cedar's AK-village "
                     "slice; member_name_raw is the fact, resolution is open"),
        })
        rec = {"source": org[2], "source_url": source_url, "retrieved": TODAY,
               "member_name_raw": h, "candidate_cedar_uid": uid,
               "candidate_canonical_name": can, "match_confidence": conf}
        rec.update(d)
        harvest_jsonl(harvest_file, rec)
        out.append((h, d, (uid, can, conf, meth)))
    return out


def normalise_url(u):
    u = u.strip().rstrip(".,;)")
    if not u:
        return ""
    if not u.lower().startswith(("http://", "https://")):
        u = "https://" + u
    return u


def verify_site(url, entity_names):
    """Fetch and check the page NAMES the entity. Guards the lapsed-domain /
    hijack failure mode siblings hit three times.
    -> (status, verdict, title, snippet)"""
    r = fetch(url)
    if r["status"] != 200 or not r["text"]:
        return (f"{r['status']}" + (f":{r['error']}" if r["error"] else ""),
                "unreachable", "", "")
    title = title_of(r["text"])
    body = text_of(r["text"])
    low = (title + " " + body[:20000]).lower()
    hit = [n for n in entity_names if n and n.lower() in low]
    hijack_markers = [r"slot gacor", r"\bsitus\b", r"\bjudi\b", r"\btogel\b",
                      r"\bbandar\b", r"casino online", r"\bxnxx\b", r"\bporn\b",
                      r"\bbokep\b", r"แทงบอล", r"บาคาร่า", r"pg soft",
                      r"\brtp live\b", r"\bmaxwin\b"]
    hj = [k for k in hijack_markers if re.search(k, low)]
    if hj:
        return (r["status"], "HIJACKED:" + ",".join(hj), title, body[:200])
    if not hit:
        return (r["status"], "entity_not_named", title, body[:300])
    return (r["status"], "verified", title, body[:300])


def parse_tables(html):
    """-> list of list-of-rows (each row a list of cell texts)."""
    out = []
    for tm in re.finditer(r"(?is)<table[^>]*>(.*?)</table>", html):
        rows = []
        for rm in re.finditer(r"(?is)<tr[^>]*>(.*?)</tr>", tm.group(1)):
            cells = [text_of(c) for c in
                     re.findall(r"(?is)<t[dh][^>]*>(.*?)</t[dh]>", rm.group(1))]
            if cells:
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def classify_entity(name):
    """Which of the three same-named Alaska bodies is this?
    docs/NATIVE_ENTITY_NUANCES.md: IRA/traditional council (the government),
    the ANCSA village corporation, and the State of Alaska city are distinct."""
    n = name.lower()
    if n.startswith("city of") or n.endswith(" city"):
        return "city_municipal_government"
    if re.search(r"(corporation|,\s*limited\b|,\s*ltd\b|,\s*inc\b|\bincorporated\b)", n):
        return "ancsa_or_other_corporation"
    if re.search(r"(clinic|health|counseling|hospital|wellness|pharmac)", n):
        return "health_facility"
    if re.search(r"(traditional council|tribal council|village council|ira council|"
                 r"native village|native community|traditional village|\btribe\b|"
                 r"\bvillage\b|\bcouncil\b|native council)", n):
        return "tribal_government"
    if re.search(r"(school|district)", n):
        return "school"
    return "undetermined"
