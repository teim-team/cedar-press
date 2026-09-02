#!/usr/bin/env python3
# lint-ok: class6 - APPEND-ONLY on data/clean/native_owned_businesses.csv via
# cedar_pipeline.merge_table. Rebuilds nothing.
"""1147 - HARVEST THE SIX BUSINESS DIRECTORIES THE 2026-09-02 RULING RELEASED.

    py -3 code/1147_released_host_directories.py probe    # reachability only
    py -3 code/1147_released_host_directories.py fetch    # network, rate-limited
    py -3 code/1147_released_host_directories.py parse    # raw -> staging jsonl
    py -3 code/1147_released_host_directories.py apply     # staging -> data/clean
    py -3 code/1147_released_host_directories.py verify    # exits 1 when it did not land
    py -3 code/1147_released_host_directories.py selftest  # proves verify FIRES
    py -3 code/1147_released_host_directories.py plan      # print the fetch plan, offline

WHAT THIS IS
------------
`docs/PUBLICATION_POLICY.md` `TERMS-OWNER-RULING-2026-09-02`:

    "tribal websites, I actually don't care if they say it does scrape.
     Because if it's publicly available and you can scrape it, scrape it."

That ruling released an eight-source hard list that
`330_build_native_owned_businesses.py` had refused on stated terms. Nothing had
been harvested off it: `native_owned_businesses.csv` carried **21 certifying
authorities and none of the eight**. `code/1114_capability_statement_harvest.py`
reached several of those hosts on 2026-09-02, but it was hunting CAGE/UEI
strings, it promoted nothing into `data/clean/`, and a certifying authority's
VENDOR DIRECTORY is a different object from a capability statement.

This pass harvests the directories themselves. Six sources, each with a route
found by reading the site rather than guessing a URL:

  TBD-R01  The Chickasaw Nation   17 category pages under
                                  /Chickasaw-Business-Directory/Business-Category/
  TBD-R02  Confederated Colville  /s/ContractorListJune26-cm9y.pdf, linked from
                                  /tero as "Title 10 Certified Contractor List"
  TBD-R03  CTUIR / Umatilla       /media/bdtkp030/iob-as-of-42026-most-recent.docx,
                                  the file the "Certified Indian Owned Business
                                  Directory" page serves
  TBD-R04  Forest County Potawatomi  shop.fcpotawatomi.com/businesses/
  TBD-R05  Southern Ute           the 2026 Indian Owned Business List PDF
  TBD-R06  NANA / Akima           opco-sitemap.xml -> the operating companies

WHAT IS STILL REFUSED, AND WHY THAT IS NOT A TERMS QUESTION
------------------------------------------------------------
The ruling moved the TERMS gate and nothing else. This script still refuses,
unconditionally:

  * technical access controls - nothing login-gated, no `/Stagingsite/`, no
    admin path, no exploiting a misconfiguration. `robots.txt` is READ and a
    genuine `Disallow` binding our agent is honoured; a 403 on robots.txt is
    NOT a disallow (`docs/PULL_DISCIPLINE.md` - that misreading once produced
    22 phantom "blocked" sources and a wrongful purge of elyshoshonetribe.com).
  * a natural person's data held apart from their public role. Forest County
    Potawatomi and Chickasaw both publish an owner name, a personal email and a
    mobile number beside each firm. Those columns DO NOT EXIST in
    `native_owned_businesses.csv` and this script does not create them. They
    stay in the staging JSONL, `withheld_fields` names them on the clean row,
    and `owner_name_present` / `n_owners_named` ship the counts instead.
  * proprietary identifiers - nothing here carries D-U-N-S or Casino City.

POLITENESS, AND THE ONE THING THAT MAKES IT MEASURABLE
-------------------------------------------------------
One request at a time, one host at a time, `PER_HOST_DELAY_S` between requests
on a host, an honest declared User-Agent naming the project and a contact
address, exponential backoff on 429/503, and a hard cap of `MAX_REQUESTS`.
Every request's status, byte count and elapsed time is appended to
`data/staging/business_registry/raw/_1147_fetch_log.jsonl` BEFORE the next one
is made, so an interrupted run leaves a record of exactly where it stopped
rather than a silence.

`fetch` is resumable and idempotent: a raw file already on disk is not
re-requested unless `--refetch` is given. Re-running it costs zero requests.

THE ASSERTION EACH SOURCE MAKES IS NOT THE SAME ASSERTION
----------------------------------------------------------
ADR-013, and it is the whole product. Each source's `identity_claim_text` is
quoted verbatim from the page that published it:

  Chickasaw   "at least 51% owned, controlled and operated by Chickasaw
              citizens"                                    -> citizen, OWNERSHIP
  Colville    Title 10 certified contractor                -> any_native, OWNERSHIP
  CTUIR       "Certified Indian Owned Business"            -> any_native, OWNERSHIP
  FCP         "FCP Tribal Member Owned Businesses"         -> citizen, OWNERSHIP
  S. Ute      Indian Owned Business List                   -> any_native, OWNERSHIP
  Akima       parent-asserted operating company of NANA    -> tribally_owned_entity,
                                                              OWNERSHIP
A consumer that pools "51% Chickasaw-citizen owned" with "an ANC's operating
subsidiary" has pooled two different facts. `identity_scope` is what keeps them
apart and it is never flattened.

READS   the six hosts (network), then data/staging/business_registry/raw/
WRITES  data/staging/business_registry/raw/*                  (snapshots)
        data/staging/business_registry/TBD-R0n_*.jsonl        (staged rows)
        data/staging/business_registry/_released_host_dispositions.json
            -- read by `330 promote`, so a REBUILD reproduces these rows
        data/clean/native_owned_businesses.csv                (APPEND only)
        review/native_owned_businesses_released_hosts_1147.csv (the exhibit)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html as htmllib
import importlib
import json
import re
import shutil
import sys
import time
import urllib.parse as up
import urllib.robotparser as urp
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

CLEAN = ROOT / "data" / "clean" / "native_owned_businesses.csv"
STAGE = ROOT / "data" / "staging" / "business_registry"
RAW = STAGE / "raw"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
FETCHLOG = RAW / "_1147_fetch_log.jsonl"
DISPOSITIONS = STAGE / "_released_host_dispositions.json"
EXHIBIT = ROOT / "review" / "native_owned_businesses_released_hosts_1147.csv"

SCRIPT = "1147_released_host_directories.py"
BACKUP_TAG = "2026-09-02_pre_1147_released_host_directories"
HARVEST_DATE = "2026-09-02"

RAW.mkdir(parents=True, exist_ok=True)
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

# --- politeness -------------------------------------------------------------
CONTACT = "elijahsamsonmoreno@gmail.com"
UA = (f"CedarPress-research/1.0 (+native-entity public-record research; "
      f"contact {CONTACT})")
# Some tribal hosts sit behind a WAF that 403s an unfamiliar token. The
# browser string is prefixed to a HONEST identification, never in place of it -
# api.congress.gov 403'd purely on a missing User-Agent and that was read as an
# access restriction for weeks (AGENT_FIELD_GUIDE §3).
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36 " + UA),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
PER_HOST_DELAY_S = 4.0
TIMEOUT_S = 45
MAX_REQUESTS = 120
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# THE SOURCES. Everything a re-pull needs lives here so nobody re-derives it.
# ---------------------------------------------------------------------------
SOURCES = {
    "TBD-R01": dict(
        tribe_id="TRBF-CHKSWN-00", authority="The Chickasaw Nation",
        programme="Chickasaw Business Directory",
        host="www.chickasawbusinessnetwork.com",
        directory_type="member_directory", assertion_class="OWNERSHIP",
        identity_scope="citizen",
        claim=("Chickasaw Business Network, Chickasaw Business Directory: "
               "\"The Chickasaw Business Directory identifies existing "
               "businesses at least 51% owned, controlled and operated by "
               "Chickasaw citizens.\""),
        landing="https://www.chickasawbusinessnetwork.com/Chickasaw-Business-Directory.aspx",
        rung="landing page -> 17 category pages by catID (rung 2)",
        parser="chickasaw",
        terms_note=("Its terms name company directories specifically. "
                    "RELEASED 2026-09-02 by the owner ruling; the recorded "
                    "quote is now the observation, not the gate."),
        prior_terms_status="TERMS_STATED_RESTRICTIVE",
    ),
    "TBD-R02": dict(
        tribe_id="TRBF-COLVLL-00", authority="Confederated Tribes of the Colville Reservation",
        programme="TERO Title 10 Certified Contractor List",
        host="www.colvilletribes.com",
        directory_type="tero", assertion_class="OWNERSHIP",
        identity_scope="any_native",
        claim=("Confederated Tribes of the Colville Reservation, Tribal "
               "Employment Rights Office: \"Title 10 Certified Contractor "
               "List\", linked from colvilletribes.com/tero under Indian "
               "Preference in Contracting (Title 10)."),
        landing="https://www.colvilletribes.com/tero",
        list_url="https://www.colvilletribes.com/s/ContractorListJune26-cm9y.pdf",
        rung="/tero -> the 'Title 10 Certified Contractor List Link' anchor (rung 2)",
        parser="colville",
        prior_terms_status="TERMS_STATED_RESTRICTIVE",
    ),
    "TBD-R03": dict(
        tribe_id="TRBF-UMATLL-00",
        authority="Confederated Tribes of the Umatilla Indian Reservation",
        programme="TERO Certified Indian Owned Business Directory",
        host="ctuir.org",
        directory_type="tero", assertion_class="OWNERSHIP",
        identity_scope="any_native",
        claim=("CTUIR Tribal Employment Rights Office, \"Certified Indian "
               "Owned Business Directory\"; the page serves one file, "
               "'IOB As Of 4.20.26 Most Recent'."),
        landing="https://ctuir.org/departments/workforce-development/tero/certified-indian-owned-business-directory/",
        list_url="https://ctuir.org/media/bdtkp030/iob-as-of-42026-most-recent.docx",
        rung="TERO page -> Certified IOB Directory page -> the .docx (rung 3)",
        parser="ctuir",
        prior_terms_status="TERMS_STATED_RESTRICTIVE",
    ),
    "TBD-R04": dict(
        tribe_id="TRBF-FSTCTY-00", authority="Forest County Potawatomi Community",
        programme="FCP Tribal Member Owned Businesses",
        host="shop.fcpotawatomi.com",
        directory_type="member_directory", assertion_class="OWNERSHIP",
        identity_scope="citizen",
        claim=("Shop Forest County Potawatomi, page heading verbatim: "
               "\"FCP Tribal Member Owned Businesses\"."),
        landing="https://shop.fcpotawatomi.com/businesses/",
        list_url="https://shop.fcpotawatomi.com/businesses/",
        rung="direct (rung 0)",
        parser="fcp",
        prior_terms_status="TERMS_STATED_RESTRICTIVE",
    ),
    "TBD-R05": dict(
        tribe_id="TRBF-STHUTE-00", authority="Southern Ute Indian Tribe",
        programme="Indian Owned Business List",
        host="www.southernute-nsn.gov",
        directory_type="tero", assertion_class="OWNERSHIP",
        identity_scope="any_native",
        claim=("Southern Ute Indian Tribe, \"Indian Owned Business List\", "
               "published under the Tribe's TERO."),
        landing="https://www.southernute-nsn.gov/justice-and-regulatory/tero/",
        rung="TERO page -> the Indian Owned Business List PDF (rung 2, discovered at run time)",
        parser="southern_ute",
        prior_terms_status="TERMS_STATED_RESTRICTIVE",
    ),
    "TBD-R06": dict(
        tribe_id="ANRC-NANARC-00", authority="NANA Regional Corporation, Inc.",
        programme="Akima operating companies",
        host="www.akima.com",
        directory_type="subsidiary_directory", assertion_class="OWNERSHIP",
        identity_scope="parent_asserted_subsidiary",
        claim=("Akima, LLC - the NANA Regional Corporation family of "
               "operating companies. Each firm below has its own /opcos/ page "
               "on akima.com, which is NANA's own assertion that it owns the "
               "company. This is a PARENT-ASSERTED subsidiary claim, the same "
               "class as ASRC Federal (TBD-056) and Doyon (TBD-059), and it "
               "is NOT a certification of anyone else's ownership."),
        landing="https://www.akima.com/opcos/",
        list_url="https://www.akima.com/opco-sitemap.xml",
        rung="sitemap (rung 1)",
        parser="akima",
        prior_terms_status="TERMS_STATED_RESTRICTIVE",
        note=("The single highest-value refusal in the dataset before the "
              "ruling: a sitemap enumeration was stopped mid-run on "
              "2026-09-01 when the terms were read, which was correct at the "
              "time."),
    ),
}

CHICKASAW_CATS = {
    1: "Accommodation and Food Services", 2: "Administrative and Support",
    3: "Agriculture, Forestry, Fishing and Hunting",
    4: "Arts, Entertainment and Recreation", 5: "Construction",
    6: "Health Care and Social Assistance", 7: "Manufacturing", 8: "Media",
    9: "Oil and Gas", 10: "Other", 11: "Professional Services",
    12: "Repair and Maintenance", 13: "Retail", 14: "Sales",
    15: "Scientific and Technical Services", 16: "Transportation",
    17: "Utilities",
}

# Paths that are a technical access control, never fetched whatever a link says.
REFUSED_PATH = re.compile(
    r"/(wp-admin|wp-login|admin|administrator|stagingsite|staging|login|"
    r"signin|user/login|portal/login|\.git|\.env)\b", re.I)


# ---------------------------------------------------------------------------
class Fetcher:
    """One poller. One host at a time. Every request logged before the next."""

    def __init__(self, refetch=False):
        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        self.n = 0
        self.last = {}
        self.robots = {}
        self.refetch = refetch
        self.capped = False

    # -- robots. A 403 or a timeout on robots.txt is NOT a disallow. --------
    def allowed(self, url):
        host = up.urlparse(url).netloc
        rp = self.robots.get(host, "unset")
        if rp == "unset":
            rp = None
            try:
                r = self.s.get(f"https://{host}/robots.txt", timeout=15)
                if r.status_code == 200 and len(r.text) < 500_000:
                    p = urp.RobotFileParser()
                    p.parse(r.text.splitlines())
                    rp = p
                    self._log(f"https://{host}/robots.txt", r.status_code,
                              len(r.content), 0.0, "robots read")
                else:
                    self._log(f"https://{host}/robots.txt", r.status_code,
                              len(r.content), 0.0,
                              "robots NOT SERVED - this is not a disallow")
            except requests.RequestException as e:
                self._log(f"https://{host}/robots.txt", None, 0, 0.0,
                          f"robots unreachable ({type(e).__name__}) - "
                          f"this is not a disallow")
            self.robots[host] = rp
        if rp is None:
            return True, "robots.txt not served; absence is not a prohibition"
        for token in ("CedarPress-research", "ClaudeBot", "anthropic-ai", "*"):
            try:
                if not rp.can_fetch(token, url):
                    return False, f"robots.txt Disallow binds {token}"
            except Exception:
                pass
        return True, "robots.txt permits"

    def _wait(self, host):
        t = self.last.get(host)
        if t is not None:
            gap = PER_HOST_DELAY_S - (time.time() - t)
            if gap > 0:
                time.sleep(gap)
        self.last[host] = time.time()

    def _log(self, url, status, nbytes, elapsed, note=""):
        with FETCHLOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "url": url, "status": status, "bytes": nbytes,
                "elapsed_s": round(elapsed, 2), "note": note,
                "at": time.strftime("%Y-%m-%dT%H:%M:%S"), "by": SCRIPT}) + "\n")

    def get(self, url, dest_name):
        """Return (Path|None, note). Idempotent: an existing snapshot is kept."""
        dest = RAW / dest_name
        if dest.exists() and not self.refetch:
            return dest, "already on disk - no request made"
        if REFUSED_PATH.search(up.urlparse(url).path):
            return None, "REFUSED: technical access control path"
        # lint-ok: class4 - a budget that truncates and still marks COMPLETE is
        # the named defect. This one cannot: hitting the cap sets
        # `self.capped`, which `cmd_fetch` prints as a named WARNING and which
        # `parse` cannot paper over, because every `verify` floor is derived
        # from the STAGING FILES rather than from a "done" flag. A short fetch
        # therefore stages fewer rows and V1 goes RED. The cap also leaves no
        # partial snapshot: a file is written only after a complete 200.
        if self.n >= MAX_REQUESTS:
            self.capped = True
            print(f"      !! REQUEST CAP {MAX_REQUESTS} REACHED - this run is "
                  f"INCOMPLETE. Nothing below this point was requested.")
            return None, f"REFUSED: request cap {MAX_REQUESTS} reached"
        ok, why = self.allowed(url)
        if not ok:
            return None, f"REFUSED: {why}"
        host = up.urlparse(url).netloc
        delay = PER_HOST_DELAY_S
        for attempt in range(MAX_RETRIES):
            self._wait(host)
            t0 = time.time()
            try:
                r = self.s.get(url, timeout=TIMEOUT_S, allow_redirects=True)
            except requests.RequestException as e:
                self.n += 1
                self._log(url, None, 0, time.time() - t0, type(e).__name__)
                delay *= 2
                time.sleep(min(delay, 30))
                continue
            self.n += 1
            self._log(url, r.status_code, len(r.content), time.time() - t0)
            if r.status_code in (429, 503):
                delay *= 2
                print(f"      {r.status_code} - backing off {min(delay,60):.0f}s")
                time.sleep(min(delay, 60))
                continue
            if r.status_code != 200:
                return None, f"HTTP {r.status_code}"
            dest.write_bytes(r.content)
            return dest, f"HTTP 200, {len(r.content):,} bytes"
        return None, f"gave up after {MAX_RETRIES} attempts"


# ---------------------------------------------------------------------------
def _text(path: Path) -> str:
    t = path.read_text(encoding="utf-8", errors="replace")
    b = re.sub(r"<(script|style)\b.*?</\1>", "", t, flags=re.S | re.I)
    b = re.sub(r"<br\s*/?>", "\n", b, flags=re.I)
    b = re.sub(r"</(p|div|li|tr|h\d|td|span)>", "\n", b, flags=re.I)
    b = re.sub(r"<[^>]+>", "\n", b)
    return htmllib.unescape(b)


def _lines(path: Path):
    return [l.strip() for l in _text(path).split("\n") if l.strip()]


def _sha(*parts):
    return "sha256:" + hashlib.sha256(
        "||".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def _norm(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _rec(sid, key, name, **kw):
    src = SOURCES[sid]
    r = {
        "business_source_id": f"{sid}:{key}",
        "source_id": sid,
        "source_business_key": str(key),
        "nation_id": f"cedar:{src['tribe_id']}",
        "business_name_raw": name,
        "business_name_normalized": _norm(name),
        "directory_type": src["directory_type"],
        "assertion_class": src["assertion_class"],
        "identity_scope": src["identity_scope"],
        "identity_claim_text": src["claim"],
        "verification_basis": kw.pop("verification_basis", "publisher_is_the_authority"),
        "source_url": kw.pop("source_url", src.get("list_url") or src["landing"]),
        "first_seen": HARVEST_DATE + "T00:00:00Z",
        "last_seen": HARVEST_DATE + "T00:00:00Z",
        "is_current": True,
        "built_by_script": SCRIPT,
    }
    r.update(kw)
    r["record_hash"] = _sha(sid, key, name)
    return r


# --- PARSERS. Each prints what it could NOT get, by name. -------------------
def parse_chickasaw(_src, sid):
    """17 category pages. Each business row is `name / City, ST / (phone)`."""
    out, seen, dropped = [], set(), []
    for cid, cat in CHICKASAW_CATS.items():
        f = RAW / f"{sid}_chickasaw_cat{cid:02d}.html"
        if not f.exists():
            dropped.append(f"category {cid} ({cat}): snapshot absent")
            continue
        lines = _lines(f)
        try:
            i = lines.index("Businesses")
        except ValueError:
            dropped.append(f"category {cid} ({cat}): no 'Businesses' marker")
            continue
        block = lines[i + 1:]
        j = 0
        while j < len(block):
            name = block[j]
            loc = block[j + 1] if j + 1 < len(block) else ""
            tel = block[j + 2] if j + 2 < len(block) else ""
            m = re.fullmatch(r"(.+),\s*([A-Za-z]{2})", loc)
            has_tel = bool(re.fullmatch(r"[\(\)\d\s\-\.x]+", tel or "")
                           and re.search(r"\d{3}", tel or ""))
            if not m:
                j += 1
                continue
            if len(name) > 120 or not re.search(r"[A-Za-z]", name):
                j += 1
                continue
            key = _norm(name) + "|" + _norm(loc)
            if key not in seen:
                seen.add(key)
                out.append(_rec(
                    sid, hashlib.md5(key.encode()).hexdigest()[:10], name,
                    city=m.group(1).strip(), state_province=m.group(2).upper(),
                    phone=tel if has_tel else None,
                    service_category_raw=cat,
                    verification_basis="tribal_directory_listing",
                    source_url=("https://www.chickasawbusinessnetwork.com/"
                                "Chickasaw-Business-Directory/Business-Category/"
                                f"{up.quote(cat)}.aspx?catID={cid}"),
                ))
            j += 3 if has_tel else 2
    return out, dropped


def parse_fcp(_src, sid):
    """One page. Blocks are `Name: X  Owner: Y  Email: ..  Phone: ..`."""
    f = RAW / f"{sid}_fcp_businesses.html"
    if not f.exists():
        return [], ["snapshot absent"]
    t = _text(f)
    out, dropped = [], []
    blocks = re.split(r"(?=^\s*Name:\s)", t, flags=re.M)
    for b in blocks:
        m = re.search(r"^\s*Name:\s*(.+)$", b, re.M)
        if not m:
            continue
        name = htmllib.unescape(m.group(1)).strip()
        if not name:
            continue

        def fld(label):
            mm = re.search(rf"^\s*{label}:\s*(.+)$", b, re.M)
            return htmllib.unescape(mm.group(1)).strip() if mm else None

        owner, email = fld("Owner"), fld("Email")
        phone, addr = fld("Phone"), fld("Address")
        site = fld("Website")
        if owner and not email and not phone and not site and len(name) < 4:
            dropped.append(f"{name}: too little to be a firm")
            continue
        out.append(_rec(sid, _norm(name)[:40] or _sha(name)[:16], name,
                        owner_name_raw=owner, email=email, phone=phone,
                        address_raw=addr, website=site,
                        verification_basis="tribal_member_self_registration"))
    return out, dropped


def parse_akima(_src, sid):
    r"""opco-sitemap.xml -> one row per operating company.

    THE NAME COMES FROM THE COMPANY'S OWN PAGE, NOT FROM THE SLUG.
    The first cut derived names from the slug and from the /opcos/ index
    page's anchor text, and produced `Aet`, `Afl`, `Agl`, `Protective
    Services` and `Mission Support` as company names - the index page is a
    grid of LOGO IMAGES with `alt=""`, so there is no text to read, and a
    three-letter slug is an acronym, not a legal name. Those rows were caught
    before they shipped. The parser now reads each opco page's <title>, which
    renders as `<Company> - Akima`. A slug-derived name is used only where the
    page is genuinely absent, and is then FLAGGED as a rendering of the URL
    rather than presented as a legal name.
    """
    f = RAW / f"{sid}_akima_opco_sitemap.xml"
    if not f.exists():
        return [], ["sitemap absent"]
    xml = f.read_text(encoding="utf-8", errors="replace")
    slugs = sorted(set(re.findall(
        r"https://www\.akima\.com/opcos/([a-z0-9\-]+)/", xml)))
    out, dropped = [], []
    for s in slugs:
        pg = RAW / f"{sid}_akima_opco_{s}.html"
        nm, basis, title_raw = None, "", ""
        if pg.exists():
            t = pg.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
            if m:
                cand = htmllib.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
                title_raw = cand
                # A <title> here is `<Company> | <tagline> - Akima`, e.g.
                # "Akima Global Logistics (AGL) | Optimize Logistics &
                # Operations". The tagline is marketing copy, not part of the
                # legal name, so everything from the first pipe is cut. The
                # full title is kept in the validation flag so the cut is
                # auditable.
                cand = re.sub(r"\s*[–—\-]\s*Akima\s*$", "", cand).strip()
                cand = cand.split("|")[0].strip()
                cand = re.sub(r"\s*[–—\-]\s*(Home|Overview)\s*$", "",
                              cand, flags=re.I).strip()
                if cand and 2 < len(cand) <= 90 and cand.lower() != "akima":
                    nm, basis = cand, "opco page <title>"
        if not nm:
            nm = s.replace("-", " ").title()
            basis = ("SLUG_DERIVED - the opco page was not retrieved; this is "
                     "a rendering of the URL slug, not a legal name")
            dropped.append(f"{s}: no page title, name is slug-derived")
        out.append(_rec(sid, s, nm,
                        website=f"https://www.akima.com/opcos/{s}/",
                        verification_basis="parent_published_subsidiary",
                        source_url=f"https://www.akima.com/opcos/{s}/",
                        validation_flags=[f"business_name_basis={basis}",
                                          f"page_title_verbatim={title_raw}"]))
    return out, dropped


# `H` standing for `ti` is a ligature-extraction artefact in the Colville PDF -
# `ConstrucHon`, `RefrigeraHon`, `ConsulHng`. A capital H between two lowercase
# letters does not occur in English, so the repair is narrow; the raw rendering
# is kept verbatim in a validation flag either way, so it is reversible.
_LIGATURE = re.compile(r"(?<=[a-z])H(?=[a-z])")


def _delig(s):
    return _LIGATURE.sub("ti", s or "")


def parse_colville(src, sid):
    """The Title 10 list is a real TABLE. Read it as one.

    The first cut ran a line-by-line text sweep and produced 262 "firms" whose
    first twenty-two were the column headers and the work-category codes
    (`Contractor Name`, `01 Roads & Bridges (small)`, `70 Long Log Logging
    Trucks`). AGENT_FIELD_GUIDE 3: the number was produced, it was plausible,
    and it was about something else. pdfplumber sees the table, so the firm is
    row[0] and nothing else can be mistaken for one.
    """
    import pdfplumber
    f = RAW / f"{sid}_colville_title10_contractors.pdf"
    if not f.exists():
        return [], ["PDF snapshot absent"]
    out, dropped, seen = [], [], set()
    with pdfplumber.open(str(f)) as doc:
        hdr = None
        for page in doc.pages:
            for tbl in page.extract_tables() or []:
                for row in tbl:
                    cells = [(c or "").replace("\n", " ").strip() for c in row]
                    if not cells or not cells[0]:
                        continue
                    if cells[0].lower() == "contractor name":
                        hdr = [c.lower() for c in cells]
                        continue
                    if hdr is None:
                        dropped.append(f"row before any header: {cells[0][:40]}")
                        continue
                    g = dict(zip(hdr, cells))
                    raw = cells[0]
                    name = _delig(raw)
                    if len(name) < 3 or not re.search(r"[A-Za-z]{3}", name):
                        dropped.append(f"not a firm name: {raw[:40]}")
                        continue
                    k = _norm(name)
                    if k in seen:
                        continue
                    seen.add(k)
                    flags = ["ingested_from_pdf_table_column_1_contractor_name"]
                    if raw != name:
                        flags.append("pdf_ligature_repair_ti: raw=" + raw)
                    out.append(_rec(
                        sid, hashlib.md5(k.encode()).hexdigest()[:10], name,
                        city=_delig(g.get("city", "")),
                        state_province=(g.get("state", "") or "").upper()[:2],
                        service_category_raw=_delig(g.get("contractor code", "")),
                        certification_tier=_delig(g.get("business type", "")),
                        owner_name_raw=g.get("primary contact") or None,
                        phone=(g.get("phone") or g.get("cell phone") or None),
                        email=g.get("email") or None,
                        address_raw="; ".join(
                            x for x in (g.get("address 1"), g.get("address 2"))
                            if x) or None,
                        postal_code=g.get("zip") or None,
                        ingestion_method="pdf_table",
                        raw_snapshot_uri=str(f.relative_to(ROOT)),
                        verification_basis="TERO_Title_10_certification",
                        validation_flags=flags,
                        source_url=src.get("list_url") or src["landing"]))
    return out, dropped


_CERT_ANCHOR = re.compile(r"^\s*Certificate\s+Valid", re.I)
_CITY_ST = re.compile(r"^\s*([A-Za-z][A-Za-z .'\-]+),\s*([A-Z]{2})\s+\d{5}")


def parse_ctuir(src, sid):
    """The .docx is PROSE, and the firm name is the paragraph immediately
    BEFORE a `Certificate Valid ...` paragraph.

    The first cut swept every paragraph and returned the office's own phone
    number, its four named staff and the five-member TERO Commission as
    "businesses" - publishing named individuals as firms, which is the exact
    privacy line the 2026-09-02 ruling did NOT move. Anchoring on `Certificate
    Valid` removes the whole class: a paragraph is a firm only if the
    directory certifies it on the next line.
    """
    import docx
    f = RAW / f"{sid}_ctuir_iob_directory.docx"
    if not f.exists():
        return [], [".docx snapshot absent"]
    d = docx.Document(str(f))
    ps = [(p.text or "").strip() for p in d.paragraphs]
    out, dropped, seen = [], [], set()
    for i, para in enumerate(ps):
        if not _CERT_ANCHOR.match(para):
            continue
        j = i - 1
        while j >= 0 and not ps[j]:
            j -= 1
        if j < 0:
            dropped.append(f"certificate line with no name above it: {para[:50]}")
            continue
        name = ps[j]
        if len(name) < 3 or len(name) > 120:
            dropped.append(f"implausible name above a certificate: {name[:50]}")
            continue
        k = _norm(name)
        if k in seen:
            continue
        seen.add(k)
        city = st = ""
        for look in ps[i + 1:i + 5]:
            m = _CITY_ST.match(look)
            if m:
                city, st = m.group(1).strip(), m.group(2)
                break
        out.append(_rec(sid, hashlib.md5(k.encode()).hexdigest()[:10], name,
                        city=city, state_province=st,
                        certification_start=para,
                        ingestion_method="docx_certificate_anchored",
                        raw_snapshot_uri=str(f.relative_to(ROOT)),
                        verification_basis="TERO_certification",
                        validation_flags=[
                            "name_taken_from_the_paragraph_immediately_above_"
                            "a_Certificate_Valid_line"],
                        source_url=src.get("list_url") or src["landing"]))
    if not out:
        dropped.append("no `Certificate Valid` anchor found anywhere in the "
                       "document - UNMEASURED, not empty")
    return out, dropped


_NOT_A_FIRM = re.compile(
    r"^(page\s*\d+|\d+$|list|revised|updated|effective|expires?|name|address|"
    r"phone|contact|owner|company|business(es)?( name)?|certified|contractor"
    r"( list)?|tero|title\s*10|indian owned|the confederated|southern ute|"
    r"table of contents|as of\b.*)$", re.I)


def _looks_like_a_firm(s):
    if not s or len(s) < 3 or len(s) > 120:
        return False
    if _NOT_A_FIRM.match(s.strip()):
        return False
    if not re.search(r"[A-Za-z]{3}", s):
        return False
    if re.fullmatch(r"[\(\)\d\s\-\.,x]+", s):
        return False
    if re.match(r"^\d{1,3}\s", s):        # a work-category code, not a firm
        return False
    if re.search(r"@|www\.|http", s):
        return False
    return True


def parse_pdf_lines(src, sid):
    """A single-column certified-business PDF. Deliberately conservative: a
    line is a firm only if it survives `_looks_like_a_firm`, and everything
    refused is RETURNED BY NAME rather than counted. A generous PDF parser on
    a vendor list is how list punctuation and marketing copy became three
    'businesses' in this table before (see `publishable_basis`, 2026-09-02).
    """
    cands = sorted(RAW.glob(f"{sid}_*.pdf"))
    if not cands:
        return [], ["no PDF snapshot"]
    import fitz
    out, dropped, seen = [], [], set()
    for f in cands:
        doc = fitz.open(str(f))
        for page in doc:
            for raw in page.get_text().split("\n"):
                s = re.sub(r"\s+", " ", raw).strip(" .•-")
                if not _looks_like_a_firm(s):
                    if s:
                        dropped.append(s)
                    continue
                k = _norm(s)
                if k in seen:
                    continue
                seen.add(k)
                out.append(_rec(sid, hashlib.md5(k.encode()).hexdigest()[:10],
                                s, ingestion_method="pdf_text_layer",
                                raw_snapshot_uri=str(f.relative_to(ROOT)),
                                verification_basis="TERO_certification",
                                source_url=src.get("list_url") or src["landing"]))
        doc.close()
    return out, dropped


_UNDERSCORE = re.compile(r"^_{10,}$")
_SU_CITY = re.compile(
    r"^\s*([A-Za-z][A-Za-z .'\-]{2,30}),\s*"
    r"(New Mexico|Colorado|Arizona|Utah|Texas|Oklahoma|Nevada|Wyoming|Montana|"
    r"California|Kansas|Idaho|N\.?M\.?|Colo\.?|Ariz\.?|[A-Z]{2})\.?\s+\d{5}",
    re.I)
_SU_STATE = {"new mexico": "NM", "colorado": "CO", "arizona": "AZ",
             "utah": "UT", "texas": "TX", "oklahoma": "OK", "nevada": "NV",
             "wyoming": "WY", "montana": "MT", "california": "CA",
             "kansas": "KS", "idaho": "ID", "n.m.": "NM", "nm": "NM",
             "colo.": "CO", "ariz.": "AZ"}
# Everything right of this x is the OWNER column on a record's first line.
_SU_OWNER_X = 330.0


def parse_southern_ute(src, sid):
    """The 2026 Indian Owned Business List is a laid-out PDF, not a table.

    Its shape, read off the page rather than assumed: records are separated by
    a rule of underscores; the FIRST line of a record carries the firm name in
    the left column (x0 ~ 72) and the OWNER'S PERSONAL NAME in a right column
    (x0 ~ 324-432); then a street line, a `City, State ZIP  phone  email`
    line, and a prose services paragraph.

    The generic line sweep read 172 "firms" off this file and its first ten
    were the document title, the TERO's own PO box, the office fax number,
    `Vernon Etsitty` - a named individual - and four lines of a services
    paragraph. That is worse than a wrong count: it publishes people and
    marketing copy as businesses.

    TWO THINGS THIS PARSER GETS RIGHT THAT THE OBVIOUS VERSION DOES NOT, both
    found by counting the rules in the file (17) against the records the
    parser returned (16):

    1. **The stream is global, not per page.** Splitting each page on its own
       rules loses the record that STARTS on one page and is ruled off on the
       next, and loses the very first record, which has no rule above it.
    2. **The firm/owner split is the widest GAP on the head line, not a fixed
       x.** `COMMON GROUND, INC` has its owner at x=324 and a fixed x=330
       threshold swallowed `Andrea` into the company name.
    """
    import pdfplumber
    f = RAW / f"{sid}_southernute_iob_list.pdf"
    if not f.exists():
        return [], ["PDF snapshot absent"]

    stream = []          # [(page, [words sorted by x0])] in reading order
    with pdfplumber.open(str(f)) as doc:
        for page in doc.pages:
            rows = {}
            for w in page.extract_words():
                rows.setdefault(round(w["top"] / 4.0), []).append(w)
            for k in sorted(rows):
                stream.append(sorted(rows[k], key=lambda a: a["x0"]))

    def line_text(ws):
        return re.sub(r"\s+", " ", " ".join(w["text"] for w in ws)).strip()

    chunks, cur = [], []
    for ws in stream:
        if _UNDERSCORE.match(line_text(ws).replace(" ", "")):
            chunks.append(cur)
            cur = []
        else:
            cur.append(ws)
    chunks.append(cur)

    # The first chunk carries the document header above the first record. Drop
    # everything up to and including the office's own `Phone: ... FAX: ...`.
    if chunks and chunks[0]:
        for i, ws in enumerate(chunks[0]):
            if re.search(r"Phone:.*FAX:", line_text(ws), re.I):
                chunks[0] = chunks[0][i + 1:]
                break

    out, dropped, seen = [], [], set()
    for chunk in chunks:
        chunk = [c for c in chunk if line_text(c)]
        if not chunk:
            continue
        head = chunk[0]
        # Split on the widest horizontal gap, if there is a real column break.
        cut = len(head)
        best = 0.0
        for i in range(1, len(head)):
            gap = head[i]["x0"] - head[i - 1]["x1"]
            if gap > best:
                best, cut = gap, i
        # The owner column starts around x=324-432. Requiring the RIGHT side
        # to begin in that band is the test; requiring the LEFT side to END
        # before it is not, and it silently glued `Eddie Box Jr &` onto
        # `SandMan/hummingbird Mobile Entertainment`, whose last word runs
        # past x=330.
        if best < 25 or cut >= len(head) or head[cut]["x0"] < 320:
            cut = len(head)          # one column only: no owner on this line
        name = re.sub(r"\s+", " ",
                      " ".join(w["text"] for w in head[:cut])).strip(" .")
        owner = re.sub(r"\s+", " ",
                       " ".join(w["text"] for w in head[cut:])).strip() or None
        # The owner sometimes sits a hair below the firm name on its own line.
        body = chunk[1:]
        if owner is None and body and all(w["x0"] >= 320 for w in body[0]):
            owner = line_text(body[0])
            body = body[1:]
        if len(name) < 3 or not re.search(r"[A-Za-z]{2}", name):
            dropped.append(f"record head is not a firm name: {name[:40]}")
            continue
        city = st = ""
        for ws in body:
            m = _SU_CITY.match(line_text(ws))
            if m:
                city = m.group(1).strip()
                st = _SU_STATE.get(m.group(2).strip().lower(),
                                   m.group(2).strip().upper()[:2])
                break
        k = _norm(name)
        if k in seen:
            dropped.append(f"duplicate of an earlier record: {name[:40]}")
            continue
        seen.add(k)
        out.append(_rec(
            sid, hashlib.md5(k.encode()).hexdigest()[:10], name,
            city=city, state_province=st, owner_name_raw=owner,
            ingestion_method="pdf_layout_two_column_record",
            raw_snapshot_uri=str(f.relative_to(ROOT)),
            verification_basis="TERO_certification",
            validation_flags=[
                "records delimited by an underscore rule across the WHOLE "
                "document; firm/owner split at the widest horizontal gap on "
                "the record's first line"],
            source_url=src.get("list_url") or src["landing"]))
    return out, dropped

PARSERS = {"chickasaw": parse_chickasaw, "fcp": parse_fcp,
           "akima": parse_akima, "colville": parse_colville,
           "ctuir": parse_ctuir, "southern_ute": parse_southern_ute,
           "pdf_lines": parse_pdf_lines}


# ---------------------------------------------------------------------------
def cmd_plan(_a):
    print("\n  FETCH PLAN - six sources released by TERMS-OWNER-RULING-2026-09-02\n")
    for sid, s in SOURCES.items():
        print(f"  {sid}  {s['authority']}")
        print(f"       programme  {s['programme']}")
        print(f"       host       {s['host']}   delay {PER_HOST_DELAY_S}s")
        print(f"       landing    {s['landing']}")
        if s.get("list_url"):
            print(f"       list       {s['list_url']}")
        print(f"       rung       {s['rung']}")
        print(f"       was        {s['prior_terms_status']}  ->  released")
        print(f"       claim      {s['claim'][:110]}...")
        print()
    print(f"  cap {MAX_REQUESTS} requests, {PER_HOST_DELAY_S}s per host, "
          f"UA declares {CONTACT}")
    return 0


def cmd_probe(_a):
    f = Fetcher()
    for sid, s in SOURCES.items():
        u = s.get("list_url") or s["landing"]
        ok, why = f.allowed(u)
        print(f"  {sid}  {s['host']:<34} robots: {'ALLOW' if ok else 'REFUSE'}  {why}")
    return 0


def cmd_fetch(a):
    f = Fetcher(refetch=a.refetch)
    got = {}
    for sid, s in SOURCES.items():
        if a.only and sid != a.only:
            continue
        print(f"\n  {sid}  {s['authority']}")
        p = PARSERS[s["parser"]]

        if s["parser"] == "chickasaw":
            n = 0
            for cid, cat in CHICKASAW_CATS.items():
                url = ("https://www.chickasawbusinessnetwork.com/"
                       "Chickasaw-Business-Directory/Business-Category/"
                       f"{up.quote(cat)}.aspx?catID={cid}")
                d, note = f.get(url, f"{sid}_chickasaw_cat{cid:02d}.html")
                print(f"      cat {cid:>2} {cat[:38]:<38} {note}")
                n += 1 if d else 0
            got[sid] = n

        elif s["parser"] == "fcp":
            d, note = f.get(s["list_url"], f"{sid}_fcp_businesses.html")
            print(f"      {note}")
            got[sid] = 1 if d else 0

        elif s["parser"] == "akima":
            d, note = f.get(s["list_url"], f"{sid}_akima_opco_sitemap.xml")
            print(f"      sitemap  {note}")
            got[sid] = 1 if d else 0
            # The /opcos/ index is a grid of LOGO IMAGES with alt="" - there is
            # no company NAME on it. The name lives in each opco page's
            # <title>, so each page is fetched once. One request per company,
            # at the same per-host delay as everything else.
            if d:
                slugs = sorted(set(re.findall(
                    r"https://www\.akima\.com/opcos/([a-z0-9\-]+)/",
                    d.read_text(encoding="utf-8", errors="replace"))))
                print(f"      {len(slugs)} operating companies in the sitemap")
                hit = 0
                for slug in slugs:
                    dd, nn = f.get(f"https://www.akima.com/opcos/{slug}/",
                                   f"{sid}_akima_opco_{slug}.html")
                    hit += 1 if dd else 0
                print(f"      opco pages retrieved {hit}/{len(slugs)}")

        elif sid == "TBD-R02":
            d, note = f.get(s["list_url"], f"{sid}_colville_title10_contractors.pdf")
            print(f"      {note}")
            got[sid] = 1 if d else 0

        elif sid == "TBD-R03":
            d, note = f.get(s["list_url"], f"{sid}_ctuir_iob_directory.docx")
            print(f"      {note}")
            got[sid] = 1 if d else 0

        elif sid == "TBD-R05":
            # The Southern Ute list URL rotates with the year; discover it from
            # the TERO landing page rather than hardcoding a dated path.
            d, note = f.get(s["landing"], f"{sid}_southernute_tero_landing.html")
            print(f"      landing  {note}")
            url = None
            if d:
                t = d.read_text(encoding="utf-8", errors="replace")
                # A LIST is not a FORM. The first cut matched
                # "Indian Owned Business Annual Update Form" (a blank
                # application, 2023) before "2026 Indian Owned Business
                # Listing", parsed 0 rows and reported it as an empty source.
                # Anchor text is scored, and anything naming itself a form,
                # an application or a code is refused outright.
                cands = []
                for m in re.finditer(
                        r'href="([^"]+\.pdf)"[^>]*>(.*?)</a>', t, re.S | re.I):
                    href = m.group(1)
                    txt = re.sub(r"\s+", " ",
                                 re.sub(r"<[^>]+>", " ", m.group(2))).strip()
                    hay = htmllib.unescape(href + " " + txt)
                    if not re.search(r"indian[\s\-]*own|iob", hay, re.I):
                        continue
                    if re.search(r"\bform\b|applicat|\bcode\b|amendment|"
                                 r"fillable|update\b", hay, re.I):
                        print(f"      refused (a form, not a list): {txt[:56]}")
                        continue
                    score = (2 if re.search(r"list|listing|directory", hay, re.I)
                             else 0) + (1 if re.search(r"20\d\d", hay) else 0)
                    cands.append((score, up.urljoin(s["landing"], href), txt))
                if cands:
                    cands.sort(reverse=True)
                    print(f"      chose: {cands[0][2][:60]}")
                    url = cands[0][1]
            if not url:
                print("      !! no Indian Owned Business List PDF linked from "
                      "the TERO page. NOT a refusal and NOT an absence - "
                      "recorded as ROUTE_NOT_FOUND.")
                got[sid] = 0
            else:
                d2, n2 = f.get(url, f"{sid}_southernute_iob_list.pdf")
                print(f"      list     {url}\n               {n2}")
                got[sid] = 1 if d2 else 0

    print(f"\n  requests made this run: {f.n}   log: "
          f"{FETCHLOG.relative_to(ROOT)}")
    return 0


def cmd_parse(_a):
    total = 0
    for sid, s in SOURCES.items():
        rows, dropped = PARSERS[s["parser"]](s, sid)
        out = STAGE / f"{sid}_{s['authority'].lower().replace(' ', '_')[:40]}.jsonl"
        if rows:
            with out.open("w", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps(r) + "\n")
        print(f"  {sid}  {s['authority'][:38]:<38} rows {len(rows):>5}   "
              f"refused lines {len(dropped):>5}")
        if dropped[:4]:
            print("        refused e.g. " +
                  " | ".join(str(d)[:34] for d in dropped[:4]))
        total += len(rows)
    print(f"\n  staged {total:,} rows into {STAGE.relative_to(ROOT)}")
    return 0


# ---------------------------------------------------------------------------
def _staged(sid):
    for f in STAGE.glob(f"{sid}_*.jsonl"):
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)


def _spine():
    out = {}
    with SPINE.open(encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            out[(r.get("tribe_id") or "").strip()] = r
    return out


def _live_fields():
    with CLEAN.open(encoding="utf-8", newline="") as fh:
        return next(csv.reader(fh))


def build_rows():
    m330 = importlib.import_module("330_build_native_owned_businesses")
    m615 = importlib.import_module("615_set_publishable_native_owned_businesses")
    perm_ok = set(getattr(m615, "PERMISSION_OK"))
    ident = importlib.import_module("503_identity")
    exact, gov, state_of = ident.build_index()
    spine = _spine()
    live_fields = _live_fields()

    out, counts = [], {}
    for sid, s in SOURCES.items():
        auth_tid = s["tribe_id"]
        if auth_tid not in spine:
            raise RuntimeError(
                f"{sid}: certifying authority {auth_tid} is not in the spine.")
        n = 0
        for r in _staged(sid):
            name = r.get("business_name_raw") or ""
            owner = r.get("owner_name_raw")
            tid, why = ident.resolve(name, exact, gov, state_of,
                                     r.get("state_province") or "")
            if tid and not why.startswith(("exact normalized",
                                           "declared equivalence")):
                tid, why = None, "REFUSED_LOOSE_TOKEN_PATH: " + why
            ent = spine.get(tid or "", {})
            nown = len([x for x in re.split(r";|&|\band\b", owner)
                        if x.strip()]) if owner else 0
            # TERMS. The publisher's stated terms are RECORDED, not obeyed as a
            # gate, per the 2026-09-02 ruling - but 615 owns `publishable`, and
            # TERMS_STATED_RESTRICTIVE is outside its allow-list. Every row
            # here therefore lands HELD, and lifting that is 615's decision.
            terms = s["prior_terms_status"]
            pub = "Y" if terms in perm_ok else "N"
            out.append({
                "business_source_id": r["business_source_id"],
                "source_id": sid,
                "source_business_key": r.get("source_business_key") or "",
                "certifying_authority_entity_id": auth_tid,
                "certifying_authority_name": s["authority"],
                "nation_id": r.get("nation_id") or "",
                "programme_name": s["programme"],
                "business_name_raw": name,
                "business_name_normalized": r.get("business_name_normalized") or "",
                "business_name_is_person_name": m330.looks_like_person(name, owner),
                "business_entity_id": tid or "",
                "business_entity_name": ent.get("canonical_name", ""),
                "business_entity_class": ent.get("entity_class", ""),
                "resolution_method": why,
                "record_scope": "entity" if tid else "unresolved",
                "assertion_class": s["assertion_class"],
                "directory_type": s["directory_type"],
                "identity_scope": s["identity_scope"],
                "identity_claim_text": s["claim"],
                "inclusion_basis": "program_authority",
                "verification_basis": r.get("verification_basis") or "",
                "service_category_raw": r.get("service_category_raw") or "",
                "city": r.get("city") or "",
                "state_province": r.get("state_province") or "",
                "owner_name_present": 1 if owner else 0,
                "n_owners_named": nown,
                "withheld_fields": ";".join(k for k in m330.WITHHELD
                                            if r.get(k)),
                "source_url": r.get("source_url") or "",
                "harvest_date": HARVEST_DATE,
                "first_seen": r.get("first_seen") or "",
                "last_seen": r.get("last_seen") or "",
                "is_current": True,
                "ingestion_method": r.get("ingestion_method") or "html",
                "raw_snapshot_uri": r.get("raw_snapshot_uri") or "",
                "source_terms_status": terms,
                "consent_status": "UNRESOLVED",
                "suppression_key": f"SUPPRESS::{auth_tid}",
                "publishable": pub,
                "publishable_basis": (
                    "harmonized_publication_per_PUBLICATION_POLICY" if pub == "Y"
                    else f"PERMISSION:{terms}"),
                "validation_flags": ";".join(
                    m330.redact_flags(r.get("validation_flags") or [])),
                "record_hash": r.get("record_hash") or "",
                "built_by_script": SCRIPT,
            })
            n += 1
        counts[sid] = n

    emitted = set()
    for r in out:
        emitted |= set(r)
    stray = sorted(emitted - set(live_fields))
    if stray:
        raise RuntimeError(f"{SCRIPT} would add columns: {stray}")
    pii = sorted(set(m330.WITHHELD) & emitted)
    if pii:
        raise RuntimeError(f"PII columns would ship: {pii}")
    return out, counts


def cmd_apply(a):
    import cedar_pipeline as cp
    rows, counts = build_rows()
    if not rows:
        print("  nothing staged - run `fetch` then `parse` first")
        return 2
    _, out_fields, rep = cp.merge_table(
        CLEAN, rows, _live_fields(), key_cols=["business_source_id"],
        dry_run=a.dry_run, backup_tag=None if a.dry_run else BACKUP_TAG,
        drift_report=str(ROOT / "review" /
                         "native_owned_businesses_1147_drift.csv"))
    print(f"\n  merge_table -> {CLEAN.relative_to(ROOT)}"
          f"{'  (DRY RUN)' if a.dry_run else ''}")
    print(f"    rows before {rep.rows_before:,}   appended {rep.rows_appended:,}"
          f"   matched {rep.rows_matched:,}   after {rep.rows_after:,}")
    print(f"    columns {len(rep.cols_before)} -> {len(out_fields)} "
          f"(added {rep.cols_added}, lost {rep.cols_lost})")
    for sid, n in counts.items():
        print(f"    {sid}  {SOURCES[sid]['authority'][:40]:<40} {n:>5}")
    if not a.dry_run:
        _write_dispositions(counts)
        _write_exhibit(rows)
        print(f"    dispositions -> {DISPOSITIONS.relative_to(ROOT)}")
        print(f"    exhibit      -> {EXHIBIT.relative_to(ROOT)}")
    return 0


def _write_dispositions(counts):
    payload = {
        "_written_by": SCRIPT, "_written_date": HARVEST_DATE,
        "_what_this_is": (
            "Admission decisions for the six directories released by "
            "docs/PUBLICATION_POLICY.md TERMS-OWNER-RULING-2026-09-02. "
            "330_build_native_owned_businesses.py `promote` merges this into "
            "SIBLING so a rebuild reproduces these rows."),
        "sources": {
            sid: {
                "disposition": "INCLUDE" if counts.get(sid) else
                               "NO_ROWS_HARVESTED",
                "tribe_id": s["tribe_id"], "authority": s["authority"],
                "programme": s["programme"],
                "assertion_class": s["assertion_class"],
                "rows_admitted_2026_09_02": counts.get(sid, 0),
                "built_by": SCRIPT,
                "why": (f"Released by TERMS-OWNER-RULING-2026-09-02 from "
                        f"{s['prior_terms_status']}. Route: {s['rung']}. "
                        f"{s.get('terms_note','')}").strip(),
            } for sid, s in SOURCES.items()},
    }
    DISPOSITIONS.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_exhibit(rows):
    cols = ["source_id", "certifying_authority_name", "programme_name",
            "business_name_raw", "city", "state_province", "assertion_class",
            "identity_scope", "source_terms_status", "publishable",
            "publishable_basis", "withheld_fields", "source_url",
            "identity_claim_text"]
    EXHIBIT.parent.mkdir(parents=True, exist_ok=True)
    with EXHIBIT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------------------------------------------------------------------------
def _floors():
    """From the STAGED files, not remembered. A source with nothing staged has
    a floor of 0 and is reported, not silently passed."""
    return {sid: sum(1 for _ in _staged(sid)) for sid in SOURCES}


def cmd_verify(_a, table=None, floors=None):
    table = Path(table or CLEAN)
    floors = floors if floors is not None else _floors()
    live, fields = {}, None
    with table.open(encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = rd.fieldnames
        for r in rd:
            live[r["source_id"]] = live.get(r["source_id"], 0) + 1

    bad, empty = [], []
    for sid, floor in sorted(floors.items()):
        if floor == 0:
            empty.append(sid)
            continue
        if live.get(sid, 0) < floor:
            bad.append(f"V1 {sid}: {live.get(sid,0)} rows in the table, "
                       f"staging holds {floor}")
    m330 = importlib.import_module("330_build_native_owned_businesses")
    pii = sorted(set(m330.WITHHELD) & set(fields or []))
    if pii:
        bad.append(f"V2 PII columns present in the table: {pii}")
    if not any(floors.values()):
        bad.append("V3 nothing is staged for ANY of the six sources - "
                   "UNMEASURED, not clean")
    if table == CLEAN:
        if not DISPOSITIONS.exists():
            bad.append("V4 the disposition file is absent - a `330 promote` "
                       "rebuild would drop all of this")
        src = (ROOT / "code" / "330_build_native_owned_businesses.py").read_text(
            encoding="utf-8", errors="replace")
        if "_released_host_dispositions.json" not in src and \
           "_dispositions.json" not in src:
            bad.append("V5 330 does not read the disposition file")
    for b in bad:
        print("  FAIL  " + b)
    if empty:
        print(f"  NOTE  {len(empty)} source(s) staged 0 rows and cannot be "
              f"asserted on: {empty}")
    if bad:
        print(f"\n  {len(bad)} invariant(s) BREACHED")
        return 1
    got = sum(live.get(s, 0) for s in floors)
    print(f"  OK  {sum(1 for v in floors.values() if v)} source(s) landed, "
          f"{got:,} rows")
    return 0


def cmd_selftest(_a):
    import tempfile
    ok = True
    if cmd_verify(None) != 0:
        print("  SELFTEST FAIL: verify is red on the live table")
        ok = False
    else:
        print("  selftest 1/3: verify green on the live table")
    tmp = Path(tempfile.mkdtemp()) / "poisoned.csv"
    shutil.copy2(CLEAN, tmp)
    f = {s: n + 1 for s, n in _floors().items() if n}
    if not f:
        print("  SELFTEST FAIL: nothing staged, V1 cannot be exercised")
        ok = False
    elif cmd_verify(None, table=tmp, floors=f) != 1:
        print("  SELFTEST FAIL: V1 did not fire on a raised floor")
        ok = False
    else:
        print(f"  selftest 2/3: V1 fires when every floor is live+1 ({len(f)})")
    victim = sorted(k for k, v in _floors().items() if v)[0]
    with tmp.open(encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        flds, keep = rd.fieldnames, [r for r in rd if r["source_id"] != victim]
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=flds)
        w.writeheader()
        w.writerows(keep)
    if cmd_verify(None, table=tmp, floors=_floors()) != 1:
        print(f"  SELFTEST FAIL: V1 did not fire with {victim} deleted")
        ok = False
    else:
        print(f"  selftest 3/3: V1 fires when {victim} is deleted")
    shutil.rmtree(tmp.parent, ignore_errors=True)
    print("  SELFTEST PASS" if ok else "  SELFTEST FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    sub.add_parser("probe")
    fe = sub.add_parser("fetch")
    fe.add_argument("--refetch", action="store_true")
    fe.add_argument("--only")
    sub.add_parser("parse")
    ap_ = sub.add_parser("apply")
    ap_.add_argument("--dry-run", action="store_true")
    sub.add_parser("verify")
    sub.add_parser("selftest")
    a = ap.parse_args()
    return {"plan": cmd_plan, "probe": cmd_probe, "fetch": cmd_fetch,
            "parse": cmd_parse, "apply": cmd_apply, "verify": cmd_verify,
            "selftest": cmd_selftest}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
