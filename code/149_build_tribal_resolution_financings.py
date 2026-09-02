#!/usr/bin/env python3
"""149_build_tribal_resolution_financings.py -- Gaming spec Step 13.

Tribal legislative archives: resolutions and council minutes that AUTHORISE
casino financing. Borrower, lender, amount, interest formula, maturity,
collateral, pledged revenues, equipment, authorisation date.

=== A RESOLUTION PROVES AUTHORISATION, NOT CLOSING

This is the same evidentiary ladder the declination build already runs, and it
is reused rather than reinvented:

    AUTHORIZED -> NIGC_REVIEWED -> EXECUTION_UNCONFIRMED -> EXECUTED_CONFIRMED
               -> CLOSED_CONFIRMED -> SUPERSEDED / TERMINATED

A council resolution sits at **AUTHORIZED** and nowhere further. It records
that the governing body voted to permit an officer to enter a transaction. It
does not establish that the transaction was negotiated, executed, funded or
survived. Where the same tribe and counterparty already appear in
`data/clean/nigc_declination_letters.csv` (327 letters, already built and NOT
rebuilt here), the resolution is CROSS-REFERENCED to it and the pair is
reported as one financing relationship, never as two deals. Counting an
authorisation and a review of the same transaction as two events double-counts,
which is exactly the caution the declination build already carries for its own
repeat counterparties.

=== WHAT THIS BUILD IS HONEST ABOUT

Tribal legislative publication is **sparse, voluntary and unindexed**. There is
no central archive; each nation decides what it posts. So the primary output of
this script is a COVERAGE table, not a row count:

    PUBLISHES     retrieved a legislative archive and read it
    WITHHOLDS     the nation states the records are not public
    NOT_FOUND     swept, naming what was swept, and did not find one
    NOT_CHECKED   nobody looked

Three traps this build is written around, all already paid for elsewhere in
this project:

  * **A broken site search is not evidence of absence.** Where a host's own
    search or sitemap fails, that is recorded as a fact about the navigation,
    and the host stays NOT_FOUND with the failure named -- never "publishes
    nothing".
  * **A 403 is not a NOT_FOUND.** A refusing host is NOT_CHECKED.
  * **A dropped connection is not a 404.** `http_status = 0` means transport
    failure and is recorded with the reading spelled out.

=== EXTRACTION IS FROM LINK TEXT AND DOCUMENT TEXT, NEVER FROM A URL

A resolution's number and subject are routinely in its link text
("TR 23-045 -- Authorizing a Credit Agreement with ..."), which is the cheapest
true evidence available. Where the document itself is retrieved, the quote comes
from the document. A row never asserts a party, an amount or a date that is not
in the quote carried on that row.

Reads  a curated list of tribal legislative hosts (below)
       data/clean/nigc_declination_letters.csv   (cross-reference only)
       data/spine/cedar_entity_spine.csv
Writes data/clean/tribal_resolution_financings.csv
       data/clean/source_coverage_tribal_legislative.csv
"""
from __future__ import annotations

import csv
import datetime as dt
import functools
import html as htmlmod
import importlib.util
import json
import os
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
RAW = ROOT / "data" / "raw" / "tribal_legislative"
CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
SCRIPT = "code/149_build_tribal_resolution_financings.py"
TODAY = dt.date.today().isoformat()
NOW = dt.datetime.now(dt.timezone.utc).isoformat()
for d in (RAW, CLEAN, REVIEW, LOGS):
    d.mkdir(parents=True, exist_ok=True)

UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
HDR = {"User-Agent": UA,
       "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
       "Accept-Language": "en-US,en;q=0.9"}
GAP = 6.0
DEADLINE_S = 40 * 60
DISK_FLOOR_GB = 6.0
PAGES_PER_HOST = 6
DOCS_PER_HOST = 12
MAX_DOC_BYTES = 25 * 1024 * 1024
START = time.time()

# Curated because a blind crawl of 574 tribal domains is neither polite nor
# productive. Each entry is a nation that (a) holds gaming and (b) is known or
# plausibly expected to post legislative material. Entry points are the
# nation's own governance landing pages; where a guess 404s that is recorded as
# a fact about the URL, not about the nation.
HOSTS = [
    ("Oneida Nation (Wisconsin)", "oneida-nsn.gov",
     ["https://oneida-nsn.gov/government/business-committee/",
      "https://oneida-nsn.gov/resources/"]),
    ("Navajo Nation", "www.navajonationcouncil.org",
     ["https://www.navajonationcouncil.org/legislations/",
      "https://www.navajonationcouncil.org/"]),
    ("Muscogee (Creek) Nation", "www.mcnnc.com",
     ["https://www.mcnnc.com/legislation/", "https://www.mcnnc.com/"]),
    ("Ho-Chunk Nation", "ho-chunknation.com",
     ["https://ho-chunknation.com/government/legislature/",
      "https://ho-chunknation.com/"]),
    ("Cherokee Nation", "www.cherokee.org",
     ["https://www.cherokee.org/about-the-nation/government/legislative/",
      "https://www.cherokee.org/"]),
    ("Saginaw Chippewa Indian Tribe", "www.sagchip.org",
     ["https://www.sagchip.org/tribalcouncil/", "https://www.sagchip.org/"]),
    ("Sault Ste. Marie Tribe of Chippewa Indians", "www.saulttribe.com",
     ["https://www.saulttribe.com/government/board-of-directors",
      "https://www.saulttribe.com/"]),
    ("Mille Lacs Band of Ojibwe", "millelacsband.com",
     ["https://millelacsband.com/government/band-assembly",
      "https://millelacsband.com/"]),
    ("Confederated Tribes of Grand Ronde", "www.grandronde.org",
     ["https://www.grandronde.org/government/tribal-council/",
      "https://www.grandronde.org/"]),
    # The four hosts below were NOT_CHECKED on the first run: every entry
    # point failed at the transport layer, which is a DNS/TLS fact about the
    # hostname string and is NOT evidence the nation publishes nothing.
    # Replaced with www-qualified or renamed hosts.
    ("Swinomish Indian Tribal Community", "www.swinomish-nsn.gov",
     ["https://www.swinomish-nsn.gov/government/senate",
      "https://www.swinomish-nsn.gov/"]),
    ("Grand Traverse Band of Ottawa and Chippewa Indians", "www.gtbindians.org",
     ["https://www.gtbindians.org/tribal-council/",
      "https://www.gtbindians.org/"]),
    ("Poarch Band of Creek Indians", "www.pci-nsn.gov",
     ["https://www.pci-nsn.gov/tribal-government/",
      "https://www.pci-nsn.gov/"]),
    ("Osage Nation", "www.osagenation-nsn.gov",
     ["https://www.osagenation-nsn.gov/who-we-are/osage-nation-congress",
      "https://www.osagenation-nsn.gov/"]),
    ("Tulalip Tribes of Washington", "www.tulaliptribes-nsn.gov",
     ["https://www.tulaliptribes-nsn.gov/Base/Government",
      "https://www.tulaliptribes-nsn.gov/"]),
    ("Prairie Band Potawatomi Nation", "www.pbpindiantribe.com",
     ["https://www.pbpindiantribe.com/tribal-council/",
      "https://www.pbpindiantribe.com/"]),
    ("Forest County Potawatomi Community", "www.fcpotawatomi.com",
     ["https://www.fcpotawatomi.com/government/",
      "https://www.fcpotawatomi.com/"]),
    ("Stockbridge-Munsee Community", "www.mohican.com",
     ["https://www.mohican.com/tribal-council/", "https://www.mohican.com/"]),
]

NAV_HINT = re.compile(
    r"resolution|legislat|tribal\s+council|business\s+committee|band\s+assembly|"
    r"council\s+minutes|meeting\s+minutes|ordinance|agenda|packet|"
    r"board\s+of\s+directors|general\s+council", re.I)

FIN_HINT = re.compile(
    r"casino\s+loan|gaming\s+loan|credit\s+agreement|promissory\s+note|"
    r"security\s+agreement|pledge\s+of\s+(?:casino|gaming|net)\s+revenues?|"
    r"depository\s+agreement|refinanc|equipment\s+financ|lender|collateral|"
    r"loan\s+agreement|bond\s+(?:issue|anticipation)|line\s+of\s+credit|"
    r"term\s+loan|guarant(?:y|ee)|indenture|forbearance|"
    r"authoriz\w+\s+(?:the\s+)?(?:borrow|execution|indebtedness)", re.I)

LENDER_HINT = re.compile(
    r"\b((?:[A-Z][\w&'\.\-]+\s+){0,4}(?:Bank|Bancorp|Capital|Financial|"
    r"Finance|Funding|Credit\s+Union|Trust\s+Company|Securities|Partners|"
    r"Holdings|Advisors|N\.A\.))\b")
MONEY = re.compile(r"\$\s?[\d,]+(?:\.\d+)?(?:\s*(?:million|billion))?")
RATE = re.compile(r"\b(?:LIBOR|SOFR|prime\s+rate|fixed\s+rate|interest\s+rate)"
                  r"[^.;]{0,60}?(\d+(?:\.\d+)?\s?%|\+\s?\d+(?:\.\d+)?\s?%)|"
                  r"\b(\d+(?:\.\d+)?\s?%)\s+(?:per\s+annum|interest)", re.I)
RESNUM = re.compile(r"\b((?:TR|RES|RESOLUTION|BC|NCA|CO|CJY|CAP|CMY|CD|CN|CF|"
                    r"CS|CO)[\s\-]?\d{1,4}[\-/]\d{2,4}|"
                    r"(?:Resolution|Res\.)\s*(?:No\.?|#)\s*[\w\-/]{2,20})", re.I)
DATE_RE = re.compile(
    r"\b((?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},?\s+\d{4}|\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}/\d{1,2}/\d{2,4})")

DOC_EXT = re.compile(r"\.(?:pdf|docx?|rtf)(?:$|\?)", re.I)
INSTRUMENT_HINT = re.compile(
    r"resolution|minutes|agenda|packet|ordinance|legislat|"
    r"tribal\s+council|business\s+committee|band\s+assembly|"
    r"board\s+of\s+directors", re.I)

A_RE = re.compile(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>", re.S | re.I)
TAG = re.compile(r"<[^>]+>")
SCRIPT_STYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)


def lock_path(h):
    return LOGS / ("_HOSTLOCK_%s.json" % h)


def read_lock(h):
    p = lock_path(h)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def pid_alive(pid):
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process -Id %d -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty Id" % int(pid)],
            capture_output=True, text=True, timeout=30).stdout
        return str(int(pid)) in out
    except Exception:
        return False


def claim_host(h, purpose):
    cur = read_lock(h)
    if cur and cur.get("active") and not cur.get("released"):
        if cur.get("pid") and pid_alive(cur["pid"]):
            cur.setdefault("queue", []).append(
                {"script": SCRIPT, "purpose": purpose, "queued_at": NOW})
            lock_path(h).write_text(json.dumps(cur, indent=1), encoding="utf-8")
            return False
    lock_path(h).write_text(json.dumps({
        "host": h, "pid": os.getpid(), "script": SCRIPT, "claimed_at": NOW,
        "active": True, "queue": [],
        "policy": "sequential, single poller, %.0fs gap, stop on first refusal"
                  % GAP, "note": purpose}, indent=1), encoding="utf-8")
    return True


def release_host(h, note=""):
    cur = read_lock(h) or {"host": h}
    cur.update({"active": False, "released": TODAY, "note": note})
    lock_path(h).write_text(json.dumps(cur, indent=1), encoding="utf-8")


def free_gb():
    return shutil.disk_usage(str(ROOT)).free / 1024 ** 3


def out_of_time():
    return (time.time() - START) > DEADLINE_S


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p, rows, cols=None):
    p = Path(p)
    if not rows:
        p.write_text("", encoding="utf-8")
        return
    cols = cols or list(rows[0].keys())
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_resolver():
    spec = importlib.util.spec_from_file_location(
        "m33", str(CODE / "33_apply_party_rulings.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.norm = functools.lru_cache(maxsize=None)(m.norm)
    m.core = functools.lru_cache(maxsize=None)(m.core)
    return m.resolve_entity


class Fetch:
    def __init__(self):
        self.s = requests.Session()

    def get(self, url, stream=False):
        """-> (http_status, content_type, bytes, reading).

        http_status 0 is a TRANSPORT failure and is never read as a 404."""
        try:
            r = self.s.get(url, headers=HDR, timeout=(15, 90), stream=stream,
                           allow_redirects=True)
        except Exception as e:
            return 0, "", b"", ("transport failure, NOT a statement about the "
                                "object: %s" % e)
        ct = r.headers.get("Content-Type", "")
        if r.status_code != 200:
            r.close()
            return r.status_code, ct, b"", (
                "HTTP %d. A 403 is a refusal and leaves this host NOT_CHECKED; "
                "a 404 is a fact about this URL only." % r.status_code)
        buf, n = [], 0
        for chunk in r.iter_content(1 << 16):
            buf.append(chunk)
            n += len(chunk)
            if n > MAX_DOC_BYTES:
                break
        r.close()
        return 200, ct, b"".join(buf), "retrieved"


def to_text(b, ct, path=None):
    if "pdf" in (ct or "").lower() or (b[:4] == b"%PDF"):
        try:
            import fitz
            doc = fitz.open(stream=b, filetype="pdf")
            t = "\n".join(p.get_text("text") for p in doc)
            doc.close()
            return t, ("TEXT_LAYER_PRESENT" if len(t.strip()) > 200
                       else "IMAGE_ONLY_SCAN_OCR_BACKLOG")
        except Exception as e:
            return "", "PDF_PARSE_FAILED:%s" % e
    t = b.decode("utf-8", "replace")
    t = SCRIPT_STYLE.sub(" ", t)
    t = htmlmod.unescape(TAG.sub(" ", t))
    return re.sub(r"[ \t\xa0]+", " ", t), "HTML"


def sentences(t):
    for s in re.split(r"(?<=[.;])\s+|\n{2,}", t):
        s = re.sub(r"\s+", " ", s).strip()
        if 25 <= len(s) <= 1200:
            yield s


def main():
    print("149 tribal legislative financings  free=%.1f GB" % free_gb())
    spine = read_csv(ROOT / "data" / "spine" / "cedar_entity_spine.csv")
    rez = load_resolver()
    declin = read_csv(CLEAN / "nigc_declination_letters.csv")
    dec_by_tribe = {}
    for d in declin:
        if d.get("tribe_entity_id"):
            dec_by_tribe.setdefault(d["tribe_entity_id"], []).append(d)
    print("  spine %d entities; %d declination letters keyed to %d tribes "
          "(cross-reference only, not rebuilt)"
          % (len(spine), len(declin), len(dec_by_tribe)))

    rows, cov = [], []
    f = Fetch()
    for tribe_name, host, entries in HOSTS:
        if out_of_time():
            cov.append({"tribe": tribe_name, "host": host,
                        "status": "NOT_CHECKED", "n_pages": 0, "n_docs": 0,
                        "n_rows": 0,
                        "evidence": "wall-clock deadline reached before this "
                                    "host was swept. Unfinished work, not a "
                                    "finding about the nation.",
                        "urls_swept": "", "retrieved_at": TODAY})
            continue
        eid, ename, how = rez(tribe_name, spine)
        if not claim_host(host, "tribal legislative archive sweep for casino "
                                "financing authorisations"):
            cov.append({"tribe": tribe_name, "host": host,
                        "status": "NOT_CHECKED", "n_pages": 0, "n_docs": 0,
                        "n_rows": 0,
                        "evidence": "host held by another poller; queued "
                                    "rather than starting a second loop",
                        "urls_swept": "", "retrieved_at": TODAY})
            continue
        swept, statuses, docs_done, host_rows = [], [], 0, 0
        nav_pages, doc_links = list(entries), []
        try:
            seen_pages = set()
            while nav_pages and len(seen_pages) < PAGES_PER_HOST:
                url = nav_pages.pop(0)
                if url in seen_pages or out_of_time():
                    break
                seen_pages.add(url)
                st, ct, body, reading = f.get(url)
                swept.append(url)
                statuses.append(st)
                time.sleep(GAP)
                if st != 200 or not body:
                    continue
                page = body.decode("utf-8", "replace")
                for m in A_RE.finditer(page):
                    href = htmlmod.unescape(m.group(1)).strip()
                    text = re.sub(r"\s+", " ",
                                  htmlmod.unescape(TAG.sub(" ", m.group(2)))
                                  ).strip()
                    if not href or href.startswith(("#", "mailto:", "tel:",
                                                    "javascript:")):
                        continue
                    absu = urljoin(url, href)
                    if urlparse(absu).netloc.lower() != host.lower():
                        continue
                    # PASS 1 of the first run matched FIN_HINT against LINK
                    # TEXT only and returned zero rows on nine hosts that were
                    # serving 200s. That is the wrong test: a tribal document
                    # library links its instruments as "TR 24-011" or
                    # "March 2024 minutes", with the subject inside the file.
                    # Link text is kept as a fast path; a document that merely
                    # LOOKS like an instrument is now fetched and its own text
                    # is what decides.
                    is_doc = bool(DOC_EXT.search(absu))
                    if FIN_HINT.search(text):
                        doc_links.append((absu, text, url, "link_text"))
                    elif is_doc and (INSTRUMENT_HINT.search(text)
                                     or INSTRUMENT_HINT.search(href)
                                     or RESNUM.search(text)):
                        doc_links.append((absu, text, url, "document_text"))
                    elif (NAV_HINT.search(text) or NAV_HINT.search(href)) \
                            and absu not in seen_pages \
                            and len(seen_pages) + len(nav_pages) < PAGES_PER_HOST:
                        nav_pages.append(absu)

            # link text first, then instrument-shaped documents
            ordered = sorted(dict.fromkeys(doc_links),
                             key=lambda t: 0 if t[3] == "link_text" else 1)
            for absu, text, from_page, how_found in ordered:
                if docs_done >= DOCS_PER_HOST or out_of_time():
                    break
                st, ct, body, reading = f.get(absu)
                swept.append(absu)
                statuses.append(st)
                docs_done += 1
                time.sleep(GAP)
                quote, quality = text, "LINK_TEXT_ONLY"
                hit = ""
                if st == 200 and body:
                    doct, quality = to_text(body, ct)
                    hit = next((s for s in sentences(doct)
                                if FIN_HINT.search(s)), "")
                    if hit:
                        quote = hit
                # A document reached only because it LOOKS like an instrument
                # earns a row only if its own text names a financing. Without
                # that the fetch is recorded in the coverage table and nothing
                # is asserted.
                if how_found == "document_text" and not hit:
                    continue
                lender = LENDER_HINT.search(quote)
                money = MONEY.findall(quote)
                rate = RATE.search(quote)
                resn = RESNUM.search(text) or RESNUM.search(quote)
                dates = DATE_RE.findall(quote) or DATE_RE.findall(text)
                xref = dec_by_tribe.get(eid or "", [])
                rows.append({
                    "tribe": tribe_name, "entity_id": eid or "",
                    "entity_name": ename or "",
                    "entity_match_method": how,
                    "entity_tier": ("B" if str(how).startswith("contain")
                                    else ("A" if eid else "")),
                    "instrument_number": resn.group(1) if resn else "",
                    "instrument_title": text,
                    "borrower": "",
                    "borrower_basis": "NOT STATED in the quote carried on this "
                                      "row; no party is asserted that the "
                                      "quote does not name.",
                    "lender": lender.group(1).strip() if lender else "",
                    "principal_amount_text": "|".join(money[:3]),
                    "interest_formula_text": (rate.group(0) if rate else ""),
                    "maturity_text": "",
                    "collateral_text": "",
                    "pledged_revenues_text": "",
                    "authorization_date_text": "|".join(dates[:2]),
                    "financing_status": "AUTHORIZED",
                    "financing_status_basis": (
                        "A council resolution authorises; it does not execute, "
                        "close or fund. Ladder: AUTHORIZED -> NIGC_REVIEWED -> "
                        "EXECUTION_UNCONFIRMED -> EXECUTED_CONFIRMED -> "
                        "CLOSED_CONFIRMED -> SUPERSEDED / TERMINATED."),
                    "nigc_declination_cross_reference":
                        "|".join(d["cedar_opinion_id"] for d in xref[:6]),
                    "nigc_cross_reference_basis": (
                        "%d NIGC declination letters exist for this tribe. A "
                        "resolution and a declination letter covering the same "
                        "transaction are ONE financing relationship; counting "
                        "both double-counts. No transaction-level match is "
                        "asserted here." % len(xref)),
                    "measurement_type": ("LOAN_PRINCIPAL" if money else ""),
                    "measurement_type_basis": (
                        "the quote carries a principal figure" if money else
                        "NO TYPE ASSIGNED: the quote carries no figure"),
                    "confidence_tier": "B",
                    "source_authority": "%s, tribal legislative archive"
                                        % tribe_name,
                    "source_document_type": "tribal_resolution_or_minutes",
                    "source_url": absu, "source_index_url": from_page,
                    "http_status": st, "text_quality": quality,
                    "retrieved_at": TODAY, "verbatim_quote": quote,
                    "built_date": TODAY})
                host_rows += 1
        finally:
            release_host(host, "legislative sweep complete")

        ok = [s for s in statuses if s == 200]
        refused = [s for s in statuses if s in (401, 403, 429)]
        transport = [s for s in statuses if s == 0]
        if host_rows:
            status = "PUBLISHES"
            ev = ("retrieved %d pages / %d documents; %d financing "
                  "authorisations read" % (len(ok), docs_done, host_rows))
        elif refused or transport:
            status = "NOT_CHECKED"
            ev = ("host refused or dropped the connection (%d refusals, %d "
                  "transport failures). A refusal is not an absence."
                  % (len(refused), len(transport)))
        elif ok:
            status = "NOT_FOUND"
            ev = ("swept %d retrievable pages under the entry points listed in "
                  "urls_swept and found no link whose text names a casino "
                  "loan, credit agreement, promissory note, security "
                  "agreement, pledge of revenues, depository agreement, "
                  "refinancing or equipment financing. The nation may publish "
                  "such records elsewhere or not at all; this states only what "
                  "these pages held." % len(ok))
        else:
            status = "NOT_FOUND"
            ev = ("every entry point returned a non-200. These URLs are wrong "
                  "or moved; that is a fact about the URLs, not about the "
                  "nation. statuses=%s" % statuses)
        cov.append({"tribe": tribe_name, "host": host, "status": status,
                    "n_pages": len(ok), "n_docs": docs_done,
                    "n_rows": host_rows, "evidence": ev,
                    "urls_swept": " | ".join(swept[:12]),
                    "http_statuses": ",".join(str(s) for s in statuses),
                    "retrieved_at": TODAY})
        print("  %-46s %-12s pages=%2d docs=%2d rows=%2d"
              % (tribe_name[:46], status, len(ok), docs_done, host_rows))

    write_csv(CLEAN / "tribal_resolution_financings.csv", rows)
    write_csv(CLEAN / "source_coverage_tribal_legislative.csv", cov)
    print("\n=== 149 SUMMARY ===")
    print("  hosts swept        %3d" % len(cov))
    for k, v in Counter(c["status"] for c in cov).most_common():
        print("    %-14s %3d" % (k, v))
    print("  financing rows     %3d" % len(rows))
    print("  entities reached   %3d" % len({r["entity_id"] for r in rows
                                            if r["entity_id"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
