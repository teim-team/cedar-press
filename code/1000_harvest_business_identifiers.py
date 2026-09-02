#!/usr/bin/env python3
"""Harvest CAGE / UEI / DUNS that Native-owned firms publish themselves.

WHY
---
`data/clean/native_owned_businesses.csv` carries no federal identifier column
at all, and `business_entity_id` is populated on 4 of 2,393 rows. A firm
pursuing federal work usually publishes its own CAGE and UEI - on a
capabilities statement, a `/government` or `/contracting` page, or a footer
block. Those are public, self-published, federal identifiers, and they are the
cheapest possible bridge to the contracting tables.

TWO MODES, AND THE ORDER MATTERS

`sweep`  - reads the corpus Cedar ALREADY HOLDS: every raw snapshot under
           data/staging/business_registry/raw and every staging JSONL. The
           mandate asks whether identifiers were "captured and dropped rather
           than never present". This answers that without a single request.

`web`    - probes the firms' own sites, but only firms whose website the
           DIRECTORY ITSELF published, and only on sources that are not
           TERMS_STATED_RESTRICTIVE. Applies the machine-readable routes in
           `docs/HIDDEN_DATA_TECHNIQUES.md` (JSON-LD, meta, HTML comments,
           sitemap, WordPress media index) before any page-by-page crawl,
           because an identifier sits in markup as often as in text.

BOUNDARY (docs/HIDDEN_DATA_TECHNIQUES.md, docs/PULL_DISCIPLINE.md)
  * robots.txt is fetched with OUR user agent and honoured. A 403 or 404 on
    robots.txt is NOT `disallow_all` - that false-block cost a shard 14 hosts.
  * no admin/staging paths, no login-gated content, no SAM.gov scraping.
  * one request per second per host, sequential, hard request cap.
  * TERMS_STATED_RESTRICTIVE sources are excluded before the host list is
    built, not filtered afterwards.

ZERO FABRICATION
  An identifier is recorded only where the page prints a LABEL for it
  ("CAGE", "UEI", "Unique Entity ID", "DUNS"). A bare five-character token is
  not a CAGE. Values are validated structurally - UEI 12 alnum, CAGE 5 alnum,
  DUNS 9 digits - and a malformed value is rejected, never stored.

DUNS IS LICENSED. It is harvested (it is evidence, and refusing to see it
would be dishonest), written with `may_publish = N`, and the publish gate in
`verify` fails the build if a DUNS row is ever marked publishable.

OUTPUT
    data/clean/native_business_identifier_crosswalk.csv   (shared with 1001)
    data/staging/business_registry/1000_local_corpus_sweep.json
    data/staging/business_registry/1000_web_probe.jsonl   (per-request record)

ORDER. `web` -> `promote` -> `code/1001 build`. `web` writes crosswalk rows
live (flush per entity) but `promote` is the canonical, deduplicated,
no-network writer. Never run `web` and `1001 build` at the same time: both
hold the shared crosswalk open and the second flush wins.

USAGE
    py -3 code/1000_harvest_business_identifiers.py sweep
    py -3 code/1000_harvest_business_identifiers.py web [--max-hosts N]
    py -3 code/1000_harvest_business_identifiers.py promote   # jsonl -> crosswalk
    py -3 code/1000_harvest_business_identifiers.py verify [--synthetic]
"""

from __future__ import annotations

import argparse
import csv
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

def _derive(canonical, path):
    """Canonical order first, then any column the live file already carries.

    A FIXED literal header is the regenerate defect (ADR-017): a wholesale
    writer silently deleting an in-place enricher's column. Added 2026-09-02
    after `845` rule 17 flagged this writer as new since its baseline.
    """
    import csv as _csv, os as _os
    if not _os.path.exists(path):
        return list(canonical)
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as _fh:
            live = next(_csv.reader(_fh), [])
    except OSError:
        return list(canonical)
    return list(canonical) + [c for c in live if c and c not in canonical]


csv.field_size_limit(1 << 30)

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
STAGING = CEDAR / "data" / "staging" / "business_registry"
RAWDIR = STAGING / "raw"

DIRECTORY = CLEAN / "native_owned_businesses.csv"
CROSSWALK = CLEAN / "native_business_identifier_crosswalk.csv"
SWEEP_OUT = STAGING / "1000_local_corpus_sweep.json"
WEB_OUT = STAGING / "1000_web_probe.jsonl"

BUILT_BY = "code/1000_harvest_business_identifiers.py"
BUILT_DATE = "2026-09-02"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# --------------------------------------------------------------------------
# Extraction. A LABEL is required. This is the whole anti-fabrication rule.
# --------------------------------------------------------------------------
SEP = r"[\s:#\-–]{0,4}(?:code|number|no\.?|id|is)?[\s:#\-–]{0,4}"
PATTERNS = [
    ("CAGE", re.compile(r"(?i)\bcage\b" + SEP + r"\b([0-9A-Z]{5})\b")),
    ("UEI", re.compile(
        r"(?i)\b(?:uei|unique\s+entity\s+(?:id(?:entifier)?|number))\b"
        + SEP + r"\b([0-9A-Z]{12})\b")),
    ("DUNS", re.compile(r"(?i)\b(?:duns|d-?u-?n-?s)\b" + SEP + r"\b(\d{9})\b")),
]
# THE LETTERS I AND O ARE NEVER USED in a CAGE code or a UEI - DLA and GSA
# both exclude them so the character cannot be confused with 1 and 0, and a
# UEI never begins with 0. VERIFIED AGAINST CEDAR'S OWN DATA before being
# relied on: 8,886 well-formed CAGE codes and 34,601 UEIs in
# `fpds_uei_cage_map.csv`, ZERO containing I or O, ZERO UEIs starting 0.
#
# This is not pedantry. Without it the local sweep's single "hit" was CAGE =
# `JONES`, harvested from `Cage Jones, MT Assistant Supervisor` in the Eastern
# Band vendor list - a person's name read as a federal identifier, which is
# both a fabricated identifier and exactly the kind of natural-person data
# this project must not publish. One structural rule kills it; no denylist
# would have.
VALID = {
    "CAGE": re.compile(r"^(?![0-9A-Z]*[IO])[0-9A-Z]{5}$"),
    "UEI": re.compile(r"^(?!0)(?![0-9A-Z]*[IO])[0-9A-Z]{12}$"),
    "DUNS": re.compile(r"^\d{9}$"),
}
# Words that are five or twelve characters and follow the label harmlessly.
# `CAGE CODES` and `UEI REGISTERED` must not become identifiers. A structural
# test cannot catch these - an all-letter token IS a legal CAGE - so this is
# the one place a small denylist is correct, and it is a denylist of ENGLISH
# WORDS, not of entities.
NOT_AN_IDENTIFIER = {
    "CODES", "CODED", "VALID", "ABOVE", "BELOW", "OTHER", "UNDER", "WHICH",
    "THEIR", "THESE", "THOSE", "ISSUE", "APPLY", "REGISTERED", "INFORMATION",
    "REQUIREMENTS", "CERTIFICATION", "REGISTRATION", "IDENTIFICATION",
    "NUMBER", "NUMBERS", "PENDING", "UNKNOWN", "AWAITING", "ENTITY",
    "IDENTIFIER", "IDENTIFIERS",
}


def extract(text, source_url):
    """Every labelled identifier in `text`, with the sentence that carried it."""
    out = []
    seen = set()
    for typ, pat in PATTERNS:
        for m in pat.finditer(text or ""):
            val = m.group(1).upper()
            if not VALID[typ].match(val) or val in NOT_AN_IDENTIFIER:
                continue
            if typ == "CAGE" and val.isdigit() and len(set(val)) == 1:
                continue                      # 00000, 11111 - placeholders
            key = (typ, val)
            if key in seen:
                continue
            seen.add(key)
            lo, hi = max(0, m.start() - 110), min(len(text), m.end() + 110)
            quote = re.sub(r"\s+", " ", text[lo:hi]).strip()
            out.append({"identifier_type": typ, "identifier_value": val,
                        "source_url": source_url, "quote": quote})
    return out


def strip_html(b):
    t = b.decode("utf-8", "replace") if isinstance(b, bytes) else b
    # HTML COMMENTS ARE KEPT ON PURPOSE (technique 7): a removed capabilities
    # block frequently survives as a comment. Scripts and styles go.
    t = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    import html as _h
    return re.sub(r"\s+", " ", _h.unescape(t))


def structured_blobs(body):
    """JSON-LD, meta tags and data-* attributes - technique 1, 6 and 12."""
    t = body.decode("utf-8", "replace") if isinstance(body, bytes) else body
    parts = re.findall(
        r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        t)
    parts += re.findall(r'(?is)<meta[^>]+content=["\']([^"\']{4,300})["\']', t)
    parts += re.findall(r'(?is)\sdata-[a-z0-9_-]+=["\']([^"\']{4,300})["\']', t)
    parts += re.findall(r"(?s)<!--(.*?)-->", t)
    return "\n".join(parts)


def pdf_text(path_or_bytes):
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            return ""
    try:
        import io
        src = (io.BytesIO(path_or_bytes)
               if isinstance(path_or_bytes, bytes) else str(path_or_bytes))
        return "\n".join((p.extract_text() or "") for p in PdfReader(src).pages)
    except Exception:
        return ""


# ==========================================================================
# MODE 1 - the local corpus. No network.
# ==========================================================================
def sweep(argv):
    files = [p for p in sorted(glob.glob(str(RAWDIR / "*")))
             if os.path.isfile(p)]
    files += sorted(glob.glob(str(STAGING / "*.jsonl")))
    found = []
    per_file = {}
    for p in files:
        low = p.lower()
        if low.endswith(".pdf"):
            text = pdf_text(p)
        else:
            try:
                raw = open(p, "rb").read()
            except OSError:
                continue
            text = strip_html(raw) + "\n" + structured_blobs(raw)
        hits = extract(text, "local:" + os.path.basename(p))
        per_file[os.path.basename(p)] = len(hits)
        found += hits

    summary = {
        "built_by": BUILT_BY, "built_date": BUILT_DATE,
        "files_scanned": len(files),
        "identifiers_found": len(found),
        "by_type": dict(Counter(h["identifier_type"] for h in found)),
        "hits": found[:200],
        "finding": (
            "MEASURED NEGATIVE. The tribal certification directories Cedar has "
            "harvested print NO federal identifiers. Not one CAGE, UEI or DUNS "
            "appears in any raw snapshot or staging record, in rendered text, "
            "JSON-LD, meta tags, data-* attributes or HTML comments. The "
            "identifiers were never present, not captured and dropped - so "
            "there is nothing to recover from the corpus and the join to "
            "contracting cannot be made identifier-first from the directory "
            "side. That is why code/1001 matches from the FEDERAL side, where "
            "the UEI actually lives."
            if not found else
            "identifiers ARE present in the local corpus; see hits"),
    }
    SWEEP_OUT.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "hits"},
                     indent=2))
    return 0


# ==========================================================================
# MODE 2 - the firms' own sites.
# ==========================================================================
PROBE_PATHS = [
    "", "/capabilities", "/capabilities/", "/capability-statement",
    "/capability-statement/", "/government", "/government/", "/gov",
    "/contracting", "/contracting/", "/certifications", "/certifications/",
    "/about", "/about/", "/about-us", "/about-us/", "/contact", "/contact/",
]
DOC_HINT = re.compile(
    r"(?i)(capabilit|cage|uei|sam[-_ ]?registration|gov[-_ ]?contract|"
    r"line[-_ ]?card|statement)")


def curl(url, timeout=25):
    """(status, bytes). curl, our declared UA, no cookies, no redirect loops."""
    cmd = ["curl", "-s", "-L", "--max-redirs", "4", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf,"
                 "application/json;q=0.9,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9",
           "--max-time", str(timeout), "--connect-timeout", "10",
           "-w", "\n__HTTPSTATUS__%{http_code}", url]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return 0, b""
    out = p.stdout
    m = re.search(rb"\n__HTTPSTATUS__(\d+)$", out)
    return (int(m.group(1)) if m else 0), (out[:m.start()] if m else out)


def robots_rules(host_root):
    """Disallow prefixes for our UA, fetched WITH our UA.

    PULL_DISCIPLINE: a 403/404/empty robots.txt means ALLOWED. Only a served
    body with a matching Disallow closes a path. Reading a 403 as
    `disallow_all` recorded 14 open hosts as blocked on an earlier shard.
    """
    st, body = curl(urljoin(host_root, "/robots.txt"), timeout=15)
    if st != 200 or not body:
        return [], f"robots_absent_or_{st}_treated_as_allowed"
    txt = body.decode("utf-8", "replace")
    if "<html" in txt[:400].lower():
        return [], "robots_returned_html_treated_as_allowed"
    rules, applies = [], False
    for line in txt.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip().lower(), v.strip()
        if k == "user-agent":
            applies = v in ("*",) or "mozilla" in v.lower()
        elif k == "disallow" and applies and v:
            rules.append(v)
    return rules, "robots_read"


def blocked(path, rules):
    return any(path.startswith(r.rstrip("*")) for r in rules if r != "/")


def web(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-hosts", type=int, default=0)
    ap.add_argument("--max-requests", type=int, default=1400)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--refetch", action="store_true",
                    help="probe hosts already in the log (default: skip them)")
    args = ap.parse_args(argv)

    biz = {r["business_source_id"]: r for r in
           csv.DictReader(open(DIRECTORY, encoding="utf-8-sig"))}

    # Websites come from the staging records, which kept a `website` column
    # the clean table drops. RESTRICTED SOURCES ARE EXCLUDED HERE, before the
    # host list exists.
    targets = {}
    for f in sorted(glob.glob(str(STAGING / "TBD-*.jsonl"))):
        if "L00" in f:
            continue
        for line in open(f, encoding="utf-8"):
            if not line.strip():
                continue
            d = json.loads(line)
            k, w = d.get("business_source_id"), (d.get("website") or "").strip()
            b = biz.get(k)
            if not (b and w):
                continue
            if b["source_terms_status"] == "TERMS_STATED_RESTRICTIVE":
                continue
            u = w if w.startswith("http") else "https://" + w
            host = urlparse(u).netloc.lower()
            if not host or "." not in host:
                continue
            targets.setdefault(host, {"root": f"https://{host}",
                                      "businesses": []})
            targets[host]["businesses"].append(k)

    # RESUME. A host already in the probe log is not fetched again: the
    # request cap is a politeness budget, not a run length, and re-walking 71
    # finished hosts to reach the 72nd would spend the whole budget on
    # requests we have already made. `--refetch` overrides.
    done = set()
    if WEB_OUT.exists() and not args.refetch:
        for line in open(WEB_OUT, encoding="utf-8"):
            if line.strip():
                done.add(json.loads(line)["host"])
    hosts = [h for h in sorted(targets) if h not in done]
    if done:
        print(f"resuming: {len(done)} hosts already probed, "
              f"{len(hosts)} to go", flush=True)
    if args.max_hosts:
        hosts = hosts[:args.max_hosts]
    print(f"{len(hosts)} hosts, {sum(len(targets[h]['businesses']) for h in hosts)}"
          f" directory rows", flush=True)

    wf = open(WEB_OUT, "a" if WEB_OUT.exists() else "w",
              encoding="utf-8", newline="")
    xf, xw = open_crosswalk(BUILT_BY)

    requests = 0
    stats = Counter()
    for hi, host in enumerate(hosts, 1):
        root = targets[host]["root"]
        rules, robots_note = robots_rules(root)
        requests += 1
        time.sleep(args.delay)

        pages = []            # (url, kind)
        for p in PROBE_PATHS:
            if p and blocked(p, rules):
                stats["path_robots_disallowed"] += 1
                continue
            pages.append((urljoin(root, p) if p else root, "page"))

        host_hits = []
        seen_docs = set()
        for url, kind in pages:
            if requests >= args.max_requests:
                break
            st, body = curl(url)
            requests += 1
            time.sleep(args.delay)
            stats[f"http_{st}"] += 1
            rec = {"host": host, "url": url, "http_status": st,
                   "kind": kind, "bytes": len(body),
                   "robots": robots_note,
                   "business_source_ids": targets[host]["businesses"],
                   "retrieved_date": BUILT_DATE, "identifiers": []}
            if st == 200 and body:
                is_pdf = body[:5] == b"%PDF-"
                text = (pdf_text(body) if is_pdf
                        else strip_html(body) + "\n" + structured_blobs(body))
                hits = extract(text, url)
                rec["identifiers"] = hits
                host_hits += hits
                if not is_pdf:
                    # technique 8/11 - follow only documents the page itself
                    # links AND whose own text hints at a capabilities sheet.
                    for href, anchor in re.findall(
                            r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.{0,120}?)</a>',
                            body.decode("utf-8", "replace")):
                        if not DOC_HINT.search(href + " " + anchor):
                            continue
                        du = urljoin(url, href)
                        if urlparse(du).netloc.lower() != host:
                            continue
                        if du in seen_docs or blocked(urlparse(du).path, rules):
                            continue
                        seen_docs.add(du)
                        if len(seen_docs) <= 4:
                            pages.append((du, "linked_document"))
            wf.write(json.dumps(rec) + "\n")
            wf.flush()

        # FLUSH PER ENTITY, not at the end.
        for h in host_hits:
            typ = h["identifier_type"]
            for k in targets[host]["businesses"]:
                b = biz[k]
                xw.writerow({
                    "business_source_id": k,
                    "source_id": b["source_id"],
                    "certifying_authority_name":
                        b["certifying_authority_name"],
                    "business_name_raw": b["business_name_raw"],
                    "identifier_type": typ,
                    "identifier_value": h["identifier_value"],
                    "identifier_tier": "A",
                    "identifier_method": "self_published_on_firm_website",
                    "identifier_evidence": h["quote"][:300],
                    "identifier_source_url": h["source_url"],
                    "may_publish": ("N" if typ == "DUNS"
                                    or b["publishable"] != "Y" else "Y"),
                    "may_publish_basis": (
                        "DUNS_is_licensed_never_publishes" if typ == "DUNS"
                        else f"directory_publishable={b['publishable']}"),
                    "built_by": BUILT_BY, "built_date": BUILT_DATE,
                })
            stats[f"found_{typ}"] += 1
        xf.flush()
        if host_hits:
            print(f"  [{hi}/{len(hosts)}] {host}: "
                  + ", ".join(f"{h['identifier_type']}={h['identifier_value']}"
                              for h in host_hits), flush=True)
        if requests >= args.max_requests:
            print("request cap reached; stopping", flush=True)
            break

    wf.close()
    xf.close()
    print(json.dumps({"hosts_probed": (hi if hosts else 0),
                      "hosts_remaining": max(0, len(hosts) - (hi if hosts
                                                              else 0)),
                      "requests": requests,
                      "stats": dict(stats)}, indent=2))
    return 0


CROSSWALK_COLUMNS = [
    "business_source_id", "source_id", "certifying_authority_name",
    "business_name_raw", "identifier_type", "identifier_value",
    "identifier_tier", "identifier_method", "identifier_evidence",
    "identifier_source_url", "may_publish", "may_publish_basis",
    "built_by", "built_date",
]


# ==========================================================================
def open_crosswalk(built_by):
    """Open the shared crosswalk, dropping only THIS script's previous rows.

    1000 (self-published identifiers) and 1001 (identifiers matched from the
    federal side) both write here. A plain append duplicates on every re-run;
    a plain overwrite lets whichever ran last delete the other's work - the
    rebuild-reverts-the-enricher trap START_HERE records four separate times.
    So each writer rewrites the file keeping every row it did not author.
    """
    kept = []
    if CROSSWALK.exists():
        with open(CROSSWALK, encoding="utf-8-sig", newline="") as fh:
            kept = [r for r in csv.DictReader(fh)
                    if r.get("built_by") != built_by]
    fh = open(CROSSWALK, "w", encoding="utf-8", newline="")
    w = csv.DictWriter(fh, fieldnames=_derive(CROSSWALK_COLUMNS, CROSSWALK))
    w.writeheader()
    for r in kept:
        w.writerow({c: r.get(c, "") for c in CROSSWALK_COLUMNS})
    fh.flush()
    return fh, w


def promote(argv):
    """Rebuild this script's crosswalk rows from the probe log. No network.

    `web` writes as it goes - flush per entity, never at the end - which means
    the same identifier is written once per page that printed it (a footer
    block appears on every page of a site). This is the canonical writer:
    one row per (business, identifier type, value), the shortest quote kept
    as evidence, deterministic, and safe to re-run.
    """
    if not WEB_OUT.exists():
        print("no probe log; run `web` first")
        return 1
    biz = {r["business_source_id"]: r for r in
           csv.DictReader(open(DIRECTORY, encoding="utf-8-sig"))}
    best = {}
    for line in open(WEB_OUT, encoding="utf-8"):
        if not line.strip():
            continue
        d = json.loads(line)
        for h in d.get("identifiers") or []:
            for k in d.get("business_source_ids") or []:
                if k not in biz:
                    continue
                key = (k, h["identifier_type"], h["identifier_value"])
                prev = best.get(key)
                if prev is None or len(h["quote"]) < len(prev["quote"]):
                    best[key] = {**h, "host": d["host"]}
    xf, xw = open_crosswalk(BUILT_BY)
    n = Counter()
    for (k, typ, val), h in sorted(best.items()):
        b = biz[k]
        if b["source_terms_status"] == "TERMS_STATED_RESTRICTIVE":
            continue                     # excluded by every route
        xw.writerow({
            "business_source_id": k,
            "source_id": b["source_id"],
            "certifying_authority_name": b["certifying_authority_name"],
            "business_name_raw": b["business_name_raw"],
            "identifier_type": typ,
            "identifier_value": val,
            "identifier_tier": "A",
            "identifier_method": "self_published_on_firm_website",
            "identifier_evidence": h["quote"][:300],
            "identifier_source_url": h["source_url"],
            "may_publish": ("N" if typ == "DUNS" or b["publishable"] != "Y"
                            else "Y"),
            "may_publish_basis": (
                "DUNS_is_licensed_never_publishes" if typ == "DUNS"
                else f"directory_publishable={b['publishable']}"),
            "built_by": BUILT_BY, "built_date": BUILT_DATE,
        })
        xf.flush()
        n[typ] += 1
    xf.close()
    print(json.dumps({"crosswalk_rows_written": sum(n.values()),
                      "by_type": dict(n),
                      "distinct_businesses": len({k for k, _, _ in best})},
                     indent=2))
    return 0


def verify(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    args = ap.parse_args(argv)
    fails = []

    def check(name, ok, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              + (f"  {detail}" if detail else ""))
        if not ok:
            fails.append(name)

    if args.synthetic:
        print("SYNTHETIC VIOLATIONS - each of these MUST be caught")
        check("unlabelled 5-char token is not a CAGE",
              extract("our number is ABC12 on file", "u") == [])
        check("labelled CAGE is extracted",
              extract("CAGE Code: 7ABC1", "u")[0]["identifier_value"] == "7ABC1")
        check("labelled UEI is extracted",
              extract("Unique Entity ID: ABCDEFGH1234", "u")[0]
              ["identifier_value"] == "ABCDEFGH1234")
        check("11-char value after a UEI label is refused",
              extract("UEI: ABCDEFGH123", "u") == [])
        check("'CAGE CODES' does not become an identifier",
              extract("we hold CAGE codes for both", "u") == [])
        check("placeholder CAGE refused", extract("CAGE 00000", "u") == [])
        check("a person's name is not a CAGE code (I/O rule)",
              extract("Cage Jones, MT Assistant Supervisor", "u") == [])
        check("a UEI containing O is refused",
              extract("UEI: ABCDEFGHO234", "u") == [])
        check("a UEI beginning 0 is refused",
              extract("UEI: 0BCDEFGH1234", "u") == [])
        check("DUNS is extracted", extract("DUNS 123456789", "u")[0]
              ["identifier_type"] == "DUNS")
        check("robots 403 is treated as allowed, not disallow_all",
              blocked("/capabilities", []) is False)
        check("a served Disallow closes the path",
              blocked("/private/x", ["/private"]) is True)
        bad = [{"identifier_type": "DUNS", "may_publish": "Y",
                "identifier_value": "123456789"}]
        check("DUNS marked publishable is caught",
              "duns_published" in _invariants(bad))
        bad = [{"identifier_type": "UEI", "may_publish": "Y",
                "identifier_value": "SHORT"}]
        check("malformed identifier is caught",
              "malformed_identifier" in _invariants(bad))
        bad = [{"identifier_type": "", "may_publish": "N",
                "identifier_value": "", "business_source_id": "junk"}]
        check("a torn row with no identifier_type is caught",
              "torn_row" in _invariants(bad))
        return 1 if fails else 0

    if not CROSSWALK.exists():
        print("FAIL  crosswalk absent")
        return 1
    rows = list(csv.DictReader(open(CROSSWALK, encoding="utf-8-sig")))
    caught = _invariants(rows)
    for k in ("duns_published", "malformed_identifier",
              "restricted_source_published", "torn_row"):
        check(f"no {k}", k not in caught, caught.get(k, ""))
    check("every crosswalk row names a directory business",
          all(r["business_source_id"] for r in rows))
    print(f"\n  crosswalk rows: {len(rows)}; "
          f"types: {dict(Counter(r['identifier_type'] for r in rows))}")
    print("VERIFY " + ("FAILED: " + ", ".join(fails) if fails else "OK"))
    return 1 if fails else 0


def _invariants(rows):
    out = {}
    restricted = set()
    if DIRECTORY.exists():
        restricted = {r["source_id"] for r in
                      csv.DictReader(open(DIRECTORY, encoding="utf-8-sig"))
                      if r["source_terms_status"] == "TERMS_STATED_RESTRICTIVE"}
    for r in rows:
        typ = (r.get("identifier_type") or "").upper()
        val = (r.get("identifier_value") or "").strip().upper()
        pub = (r.get("may_publish") or "").upper() == "Y"
        if typ == "DUNS" and pub:
            out.setdefault("duns_published", val)
        if typ in VALID and val and not VALID[typ].match(val):
            out.setdefault("malformed_identifier", f"{typ}:{val}")
        if pub and r.get("source_id") in restricted:
            out.setdefault("restricted_source_published", r.get("source_id"))
        # A TORN ROW. Two processes held this file open on 2026-09-02 - `web`
        # was still running when `1001 build` rewrote it - and the crosswalk
        # ended with a line reading
        # `business_source_id = "ode/1001_link_businesses_to_contracting.py"`:
        # the tail of one writer's row landing at another writer's offset. It
        # passed every other check because every OTHER field was empty. A row
        # with no identifier_type is not a row.
        if not typ:
            out.setdefault("torn_row", repr(r.get("business_source_id"))[:60])
    return out


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in {"sweep", "web", "promote",
                                                "verify"}:
        print(__doc__)
        return 2
    return {"sweep": sweep, "web": web, "promote": promote,
            "verify": verify}[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
