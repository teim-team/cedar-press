#!/usr/bin/env python3
"""
105 - Florida / Seminole gaming: the compact payment series, the bond and
      audited-disclosure record, and the litigation record.

WHY THIS SCRIPT EXISTS
----------------------
Florida is the one state where the framework rule in
`docs/STATE_GAMING_FRAMEWORKS.md` points at a single tribe. One compact tribe
(Seminole Tribe of Florida) carries the entire state-side payment obligation,
the State forecasts and reports that payment four to eight times a year through
its own Revenue Estimating Conference, and the tribe finances its properties
with rated debt. Cedar already held the seed: 11 of 29 tribal bond issuances
are Seminole, 26 Florida compact terms, 12 Florida properties.

WHAT FLORIDA PUBLISHES
----------------------
1. **Office of Economic and Demographic Research (EDR), Indian Gaming Revenue
   Estimating Conference.** 39 documents, November 2010 to January 2026. Each
   carries (a) a historical table of amounts ACTUALLY RECEIVED by fiscal year,
   split General Revenue / trust fund / reserve / local distribution, (b) a
   monthly actual-collections table that foots to its own printed year total,
   and (c) forecast tables of Net Win and revenue share by game category.
2. **Florida Gaming Control Commission / DBPR Division of Pari-Mutuel
   Wagering.** Per-facility slot revenue, cardroom gross receipts and
   pari-mutuel handle - for LICENSED COMMERCIAL PERMITHOLDERS ONLY. The
   Seminole and Miccosukee properties appear in none of it.

WHAT FLORIDA AND THE FEDERAL RECORD DO NOT PUBLISH
--------------------------------------------------
- No per-property tribal figure of any kind. The regulator's per-facility
  series is a permitholder series; a tribal casino holds no permit.
- No tribe-reported Net Win. The compact requires the Tribe to give the State
  audited Net Win (Part XI.C.3), and the same compact marks what the Tribe
  gives the State "Trade Secret, Confidential and Proprietary". EDR's Net Win
  columns are the CONFERENCE'S OWN FORECAST, not a tribal report, and are
  recorded here as PROJECTED with no revenue evidence class.
- The Tribe's audited financial statements exist and are withheld BY RULE.
  Seminole Tribe of Florida files a Single Audit every year (Deloitte). Every
  one of those filings is `is_public = false` at the Federal Audit
  Clearinghouse while every non-tribal Florida auditee in the same query is
  public - 2 CFR 200.512(b)(2) exempts Indian tribes from publication.

THE THREE RULES THIS BUILD IS BUILT AROUND
------------------------------------------
1. **The Florida payment does not invert.** Both governing compacts set a
   GRADUATED schedule, not a flat rate:
     2010 Compact - 12% / 15% / 17.5% / 20% / 22.5% / 25% on Covered Games
                    Net Win, plus a Guaranteed Minimum Revenue Sharing Cycle
                    Payment for the first three cycles.
     2021 Compact - 12% -> 25% on Slot Machines, 15% -> 25% on Table Games,
                    13.75% on Sports Betting, 10% on Sports Betting placed
                    through a Qualified Pari-mutuel Permitholder brand, plus
                    a $2.5 billion Guaranteed Minimum Compact Term Payment and
                    a $400 million per-cycle floor.
   `payment / rate` is therefore NOT exact arithmetic and NEVER reaches
   EXACT_DERIVED_PROPERTY_REVENUE. What the schedule does support is a
   one-sided factual bound: every dollar of Net Win is charged at no less than
   the lowest marginal rate in the governing instrument, so
   `Net Win <= payment / rate_min` exactly. The guaranteed minimum destroys the
   other side - a payment may be a floor rather than a percentage - so no lower
   bound is emitted and `bound_basis` says so.
   The pre-existing compact parse recorded a Florida `revenue_sharing_rate=10`
   as `INVERTIBLE_FLAT_RATE`. Read against Part XI.C.1(k) that 10% is the
   bottom tier of a graduated schedule for one game category. This build does
   not use it, for the same reason 44 California rows were demoted.
2. **The base is statewide, and mobile.** Even if the rate inverted, the base
   is "Net Win received by the Tribe from the operation and play of ..."
   across all Facilities plus a STATEWIDE MOBILE sports betting product. That
   is tribe-level. No Florida derivation may be attached to a property.
3. **Seminole Tribe of Florida is not Seminole Nation of Oklahoma.** Two
   federally recognised tribes; the spine holds both (TRBF-SMNLFL-00 / FL and
   TRBF-SMNLOK-00 / OK) and the compact corpus holds Seminole Nation of
   Oklahoma compacts under filenames that differ by one word. Every entity
   resolution here must agree on state = FL or it is refused.

Stages:  discover | fetch | parse | emit   (default: all)

Writes:
  data/raw/external/fl_gaming/            raw PDFs/JSON + _SOURCE_MANIFEST.csv
  data/clean/fl_gaming_payments.csv
  data/clean/seminole_bond_disclosures.csv
  review/fl_gaming_unresolved_<date>.csv
  data/interim/105_zone_log.csv
  data/interim/105_run_summary.txt

Does NOT write: gaming_facilities.csv, gaming_capacity_official.csv, compact_*,
ca_gaming_*, wa_*, nigc_*, gaming_employment_*, subawards.csv,
consultation_events.csv, oira_*, hearing_*, earmarks.csv, np_financials.csv,
entity_*, resource_*, the ledger, the spine.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
RAW = os.path.join(ROOT, "data", "raw", "external", "fl_gaming")
CLEAN = os.path.join(ROOT, "data", "clean")
INTERIM = os.path.join(ROOT, "data", "interim")
REVIEW = os.path.join(ROOT, "review")
LOGS = os.path.join(ROOT, "logs")
for d in (RAW, CLEAN, INTERIM, REVIEW, LOGS):
    os.makedirs(d, exist_ok=True)

TODAY = dt.date.today().isoformat()
SCRIPT = "code/105_build_florida_gaming.py"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
SEC_UA = "Cedar Press research (elijahsamsonmoreno@gmail.com)"
GAP = 1.6

# ---------------------------------------------------------------------------
# Shared vocabulary and the ONE resolver. Never re-implement either.
# ---------------------------------------------------------------------------
sys.path.insert(0, CODE)
from cedar_domain import (                                   # noqa: E402
    MeasurementType, may_promote, REVENUE_EVIDENCE, NAME_TRAPS, Tier,
    INSTITUTION_CLASSES, ENTITY_CLASSES, entity_class_is_declared,
)

_spec = importlib.util.spec_from_file_location(
    "party_rulings", os.path.join(CODE, "33_apply_party_rulings.py"))
_pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pr)
resolve_entity = _pr.resolve_entity

# Enforced in code, not in prose.
assert not may_promote(MeasurementType.PROJECTED,
                       MeasurementType.ACTIVE_FLOOR_COUNT)
assert not may_promote(MeasurementType.DERIVED_BOUND,
                       MeasurementType.ACTIVE_FLOOR_COUNT)
assert "BOUNDED_DERIVED_REVENUE" in REVENUE_EVIDENCE
assert "TRIBE_LEVEL_REVENUE" in REVENUE_EVIDENCE
assert "NO_REVENUE_OBSERVATION" in REVENUE_EVIDENCE

# A Florida gaming payment file can never be about these.
#
# CORRECTED 2026-08-26 by `code/442_consolidate_entity_class_vocabulary.py`,
# the same defect as `103_build_california_gaming.py` and in the same words:
# `Native CDFI` and `Native financial institution` are NOT spine class
# strings. The spine says `Native Community Development Financial Institution`
# (64) and `Native Financial Institution` (29), so **93 entities passed a
# refusal that had never once matched**. A guard written against a name that
# does not exist reads as live and filters nothing - and the next author reads
# the constant and believes they are protected.
REFUSED_ENTITY_CLASSES = INSTITUTION_CLASSES

assert REFUSED_ENTITY_CLASSES <= ENTITY_CLASSES, (
    "REFUSED_ENTITY_CLASSES carries a string the spine does not: "
    + repr(sorted(REFUSED_ENTITY_CLASSES - ENTITY_CLASSES)))
assert all(entity_class_is_declared(c) for c in REFUSED_ENTITY_CLASSES)
# Rule 3 above, enforced. The Florida compact tribe is in Florida.
ALLOWED_STATES = {"FL"}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(p, enc="utf-8-sig"):
    with open(p, encoding=enc, newline="") as f:
        return list(csv.DictReader(f))


def claim_host(host, queue):
    """PULL_DISCIPLINE rule 2. One poller per host; append and exit otherwise."""
    p = os.path.join(LOGS, "_HOSTLOCK_%s.json" % host)
    if os.path.exists(p):
        try:
            cur = json.load(open(p))
        except Exception:
            cur = {}
        holder = (cur.get("script")
                  or (cur.get("holder") or {}).get("script") or "")
        released = cur.get("released") or (cur.get("holder") or {}).get("released")
        if holder and holder != SCRIPT and not released:
            cur.setdefault("queue", []).extend(queue)
            json.dump(cur, open(p, "w"), indent=1)
            print("  host %s already claimed by %s; queued and deferring"
                  % (host, holder))
            return False
    json.dump({"host": host, "pid": os.getpid(), "script": SCRIPT,
               "started": dt.datetime.now(dt.timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%SZ"),
               "queue": queue,
               "policy": "sequential, >=1.6s gap, no retry loop"},
              open(p, "w"), indent=1)
    return True


def release_host(host, note=""):
    p = os.path.join(LOGS, "_HOSTLOCK_%s.json" % host)
    if not os.path.exists(p):
        return
    try:
        cur = json.load(open(p))
    except Exception:
        return
    if cur.get("script") != SCRIPT:
        return
    cur["released"] = dt.datetime.now(dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    cur["note"] = note
    json.dump(cur, open(p, "w"), indent=1)


_last_hit = defaultdict(float)


def curl(url, dest=None, timeout=120, ua=None, headers=()):
    """Single-stream GET with a declared UA. Returns (status, ctype, bytes)."""
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    wait = GAP - (time.time() - _last_hit[host])
    if wait > 0:
        time.sleep(wait)
    cmd = ["curl", "-s", "-L", "-A", ua or UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf,"
                 "application/json,*/*;q=0.8",
           "--max-time", str(timeout),
           "-w", "\n__META__%{http_code}|%{content_type}", url]
    for h in headers:
        cmd[1:1] = ["-H", h]
    p = subprocess.run(cmd, capture_output=True)
    _last_hit[host] = time.time()
    out = p.stdout
    m = re.search(rb"\n__META__(\d+)\|([^\n]*)$", out)
    status = int(m.group(1)) if m else 0
    ctype = (m.group(2).decode("utf-8", "replace") if m else "")
    body = out[:m.start()] if m else out
    if dest and status == 200 and body:
        with open(dest, "wb") as f:
            f.write(body)
    return status, ctype, body


# ===========================================================================
# MANIFEST
# ===========================================================================
MANIFEST = os.path.join(RAW, "_SOURCE_MANIFEST.csv")
MAN_FIELDS = ["local_file", "source_url", "source_authority", "doc_class",
              "doc_label", "http_status", "content_type", "bytes", "md5",
              "fetched_date", "retrieval_note"]


def _load_manifest():
    if not os.path.exists(MANIFEST):
        return {}
    return {r["source_url"]: r for r in _read(MANIFEST)}


def _write_manifest(d):
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MAN_FIELDS)
        w.writeheader()
        for v in sorted(d.values(), key=lambda x: (x["doc_class"],
                                                   x["source_url"])):
            w.writerow({k: v.get(k, "") for k in MAN_FIELDS})


def _manifest_rows(*classes):
    rows = [r for r in _read(MANIFEST) if r.get("local_file")]
    if classes:
        rows = [r for r in rows if r["doc_class"] in classes]
    return rows


def _local_name(url):
    tail = url.rsplit("/", 1)[-1]
    tail = re.sub(r"%20", "_", tail)
    tail = re.sub(r"[^A-Za-z0-9._-]+", "_", tail)
    return tail[:140]


def _grab(url, doc_class, authority, label, out, ua=None, note="",
          local=None):
    fn = local or _local_name(url)
    dest = os.path.join(RAW, fn)
    st, ct, body = curl(url, dest, ua=ua)
    ok = st == 200 and len(body) > 0
    if ok and fn.lower().endswith(".pdf") and body[:5] != b"%PDF-":
        ok = False                       # HTML soft-404 served as a PDF
        if os.path.exists(dest):
            os.remove(dest)
    out[url] = dict(local_file=fn if ok else "", source_url=url,
                    source_authority=authority, doc_class=doc_class,
                    doc_label=label, http_status=st, content_type=ct,
                    bytes=len(body),
                    md5=md5(dest) if ok and os.path.exists(dest) else "",
                    fetched_date=TODAY, retrieval_note=note)
    return ok


# ===========================================================================
# STAGE 1/2 - discover + fetch
# ===========================================================================
EDR_HOST = "edr.state.fl.us"
EDR_BASE = "http://edr.state.fl.us/Content/conferences/Indian-gaming/"
FGCC_HOST = "flgaming.gov"
SC_HOST = "www.supremecourt.gov"
GOVINFO_HOST = "api.govinfo.gov"
FAC_HOST = "api.fac.gov"
EMMA_HOST = "emma.msrb.org"
SEC_HOST = "efts.sec.gov"

# The four federal-court packages that make up the West Flagler record on
# govinfo's USCOURTS collection. govinfo publishes OPINIONS only; briefs live
# on the Supreme Court's own docket, which is why both hosts are worked.
USCOURTS = [
    ("USCOURTS-dcd-1_21-cv-02192",
     "West Flagler Associates, Ltd. v. Haaland (D.D.C. 2021-11-22)"),
    ("USCOURTS-caDC-21-05265",
     "West Flagler Associates, Ltd. v. Haaland (D.C. Cir. 2023-06-30)"),
    ("USCOURTS-caDC-22-05022",
     "West Flagler Associates, Ltd. v. DOI (D.C. Cir. 2023-06-30)"),
    ("USCOURTS-dcd-1_21-cv-02513",
     "Monterra MF, LLC v. Haaland (D.D.C. 2021-11-22)"),
]
SCOTUS_DOCKETS = ["23A315"]


def stage_discover():
    """Enumerate the EDR conference archive and the FGCC document pages."""
    links = []
    if claim_host(EDR_HOST, ["EDR Indian Gaming conference archive sweep"]):
        for name, url in (("current", EDR_BASE + "index.cfm"),
                          ("archives", EDR_BASE + "archives/index.cfm")):
            st, ct, body = curl(url, os.path.join(RAW, "page_edr_%s.html" % name))
            print("  edr page %-9s %s %7d" % (name, st, len(body)))
            if st != 200:
                continue
            h = body.decode("utf-8", "replace")
            base = EDR_BASE + ("archives/" if name == "archives" else "")
            for m in re.finditer(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>",
                                 h, re.S | re.I):
                href = html.unescape(m.group(1)).strip()
                text = re.sub(r"\s+", " ", html.unescape(
                    re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
                if not href.lower().endswith((".pdf", ".xls", ".xlsx")):
                    continue
                url_abs = href if href.startswith("http") else base + href
                links.append(dict(page=name, url=url_abs, link_text=text,
                                  authority=("Florida Legislature, Office of "
                                             "Economic and Demographic "
                                             "Research")))
        release_host(EDR_HOST, "EDR archive sweep complete")

    if claim_host(FGCC_HOST, ["FGCC annual reports + per-facility statistics"]):
        for name, url in (("annual", "https://flgaming.gov/pmw/annual-reports/"),
                          ("stats", "https://flgaming.gov/pmw/statistics/")):
            st, ct, body = curl(url, os.path.join(RAW, "page_fgcc_%s.html" % name))
            print("  fgcc page %-9s %s %7d" % (name, st, len(body)))
            if st != 200:
                continue
            h = body.decode("utf-8", "replace")
            for m in re.finditer(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>",
                                 h, re.S | re.I):
                href = html.unescape(m.group(1)).strip()
                text = re.sub(r"\s+", " ", html.unescape(
                    re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
                if not href.lower().endswith(".pdf"):
                    continue
                if href.startswith("http"):
                    url_abs = href
                elif href.startswith("/"):
                    url_abs = "https://flgaming.gov" + href
                else:
                    url_abs = "https://flgaming.gov/pmw/%s/%s" % (
                        "annual-reports" if name == "annual" else "statistics",
                        href)
                links.append(dict(page="fgcc_" + name, url=url_abs,
                                  link_text=text,
                                  authority="Florida Gaming Control Commission"))
        release_host(FGCC_HOST, "FGCC document sweep complete")

    p = os.path.join(RAW, "_discovered_links.csv")
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page", "url", "link_text",
                                          "authority"])
        w.writeheader()
        w.writerows(links)
    print("  discovered %d documents" % len(links))
    return links


def stage_fetch(limit=None):
    disc = os.path.join(RAW, "_discovered_links.csv")
    links = _read(disc) if os.path.exists(disc) else stage_discover()
    out = _load_manifest()

    # ---- EDR conference documents ----------------------------------------
    edr = [r for r in links if r["page"] in ("current", "archives")]
    if edr and claim_host(EDR_HOST, ["EDR conference PDFs"]):
        n = 0
        for r in edr:
            if limit and n >= limit:
                break
            if out.get(r["url"], {}).get("http_status") == "200":
                continue
            ok = _grab(r["url"], "edr_indian_gaming_conference", r["authority"],
                       r["link_text"], out)
            n += 1
            print("    %-6s %s" % ("ok" if ok else "FAIL", r["url"][-46:]))
        release_host(EDR_HOST, "EDR conference PDFs fetched")

    # ---- FGCC: annual reports (all) + one statistics file per series ------
    # The statistics files are fetched as NEGATIVE EVIDENCE: they are the
    # per-facility revenue series Florida does publish, and no tribal property
    # appears in them. One recent file per series is enough to establish that;
    # pulling all 60 would be a pull for its own sake.
    fg = [r for r in links if r["page"].startswith("fgcc_")]
    want_stats = ("SlotRevenues2024-2025", "Cardroom2024-2025",
                  "Handle-2024-2025")
    if fg and claim_host(FGCC_HOST, ["FGCC annual reports + stats sample"]):
        for r in fg:
            u = r["url"]
            is_annual = "AnnualReport" in u
            is_stat = any(w in u for w in want_stats)
            if not (is_annual or is_stat):
                continue
            if out.get(u, {}).get("http_status") == "200":
                continue
            cls = ("fgcc_annual_report" if is_annual
                   else "fgcc_permitholder_statistics")
            ok = _grab(u, cls, r["authority"], r["link_text"], out,
                       note=("" if is_annual else
                             "fetched as negative evidence: the per-facility "
                             "series covers licensed pari-mutuel/slot "
                             "permitholders, not tribal properties"))
            print("    %-6s %s" % ("ok" if ok else "FAIL", u[-46:]))
        release_host(FGCC_HOST, "FGCC documents fetched")

    # ---- govinfo USCOURTS opinions ---------------------------------------
    if claim_host(GOVINFO_HOST, ["USCOURTS West Flagler opinion packages"]):
        for pkg, label in USCOURTS:
            gid = pkg + "-0"
            url = ("https://api.govinfo.gov/packages/%s/granules/%s/pdf"
                   "?api_key=DEMO_KEY" % (pkg, gid))
            if out.get(url, {}).get("http_status") == "200":
                continue
            ok = _grab(url, "uscourts_opinion",
                       "U.S. Government Publishing Office, govinfo USCOURTS",
                       label, out, local=gid + ".pdf")
            print("    %-6s %s" % ("ok" if ok else "FAIL", pkg))
        release_host(GOVINFO_HOST, "USCOURTS opinions fetched")

    # ---- Supreme Court docket + filed briefs ------------------------------
    if claim_host(SC_HOST, ["SCOTUS West Flagler docket + briefs"]):
        for dk in SCOTUS_DOCKETS:
            jurl = "https://www.supremecourt.gov/rss/cases/JSON/%s.json" % dk
            _grab(jurl, "scotus_docket_json", "Supreme Court of the United States",
                  "Docket %s" % dk, out, local="scotus_%s.json" % dk)
            jp = os.path.join(RAW, "scotus_%s.json" % dk)
            if not os.path.exists(jp):
                continue
            j = json.load(open(jp, encoding="utf-8"))
            for e in j.get("ProceedingsandOrder", []):
                for l in e.get("Links", []) or []:
                    if l.get("Description") not in ("Main Document",
                                                    "Lower Court Orders/Opinions"):
                        continue
                    u = l["DocumentUrl"]
                    if out.get(u, {}).get("http_status") == "200":
                        continue
                    ok = _grab(u, "scotus_filing",
                               "Supreme Court of the United States",
                               "%s %s - %s" % (dk, e.get("Date"), l.get("File")),
                               out)
                    print("    %-6s %s" % ("ok" if ok else "FAIL",
                                            (l.get("File") or "")[:44]))
        release_host(SC_HOST, "SCOTUS docket + briefs fetched")

    # ---- Federal Audit Clearinghouse -------------------------------------
    if claim_host(FAC_HOST, ["Seminole Tribe of Florida single audits"]):
        u = ("https://api.fac.gov/general?auditee_ein=eq.591415030"
             "&select=report_id,audit_year,auditee_name,auditee_ein,"
             "auditee_uei,auditee_city,auditee_state,fy_start_date,fy_end_date,"
             "is_public,total_amount_expended,auditor_firm_name,gaap_results,"
             "entity_type&order=audit_year.desc&limit=60&api_key=DEMO_KEY")
        ok = _grab(u, "fac_single_audit_index",
                   "Federal Audit Clearinghouse (GSA)",
                   "Seminole Tribe of Florida, EIN 59-1415030, all audit years",
                   out, local="fac_seminole_tribe_of_florida.json",
                   note="api.data.gov DEMO_KEY; public metadata endpoint")
        print("    %-6s FAC single audit index" % ("ok" if ok else "FAIL"))
        release_host(FAC_HOST, "FAC index fetched")

    # ---- EMMA: probe only, and record the restriction ---------------------
    if claim_host(EMMA_HOST, ["MSRB EMMA robots probe"]):
        _grab("https://emma.msrb.org/robots.txt", "emma_robots",
              "Municipal Securities Rulemaking Board, EMMA",
              "EMMA robots.txt", out, local="emma_robots.txt",
              note="two requests total; no document retrieval attempted")
        release_host(EMMA_HOST, "EMMA robots probe complete; PDFs disallowed")

    # ---- SEC full-text search: third-party holder disclosures -------------
    if claim_host(SEC_HOST, ["SEC EDGAR full-text search, Seminole bonds"]):
        for q, tag in (('"Seminole Tribe of Florida"', "all"),):
            u = ("https://efts.sec.gov/LATEST/search-index?q=%s&forms=N-Q,"
                 "N-CSR,N-CSRS,N-PORT" % q.replace(' ', '+').replace('"', '%22'))
            _grab(u, "sec_full_text_search",
                  "U.S. Securities and Exchange Commission, EDGAR full-text search",
                  "EDGAR FTS: %s in fund holdings forms" % q, out,
                  local="sec_fts_seminole_%s.json" % tag, ua=SEC_UA)
        release_host(SEC_HOST, "SEC FTS query complete")

    _write_manifest(out)
    have = [v for v in out.values() if v["local_file"]]
    print("  manifest: %d entries, %d on disk" % (len(out), len(have)))
    for k, v in Counter(v["doc_class"] for v in have).most_common():
        print("     %-34s %d" % (k, v))


def stage_fetch_sec_documents(limit=40):
    """Pull the individual EDGAR documents surfaced by full-text search."""
    p = os.path.join(RAW, "sec_fts_seminole_all.json")
    if not os.path.exists(p):
        return
    j = json.load(open(p, encoding="utf-8"))
    hits = j.get("hits", {}).get("hits", [])
    out = _load_manifest()
    if not claim_host("www.sec.gov", ["EDGAR archive documents"]):
        return
    n = 0
    for h in hits:
        if n >= limit:
            break
        _id = h.get("_id", "")
        if ":" not in _id:
            continue
        acc, doc = _id.split(":", 1)
        cik = (h.get("_source", {}).get("ciks") or ["0"])[0].lstrip("0")
        url = "https://www.sec.gov/Archives/edgar/data/%s/%s/%s" % (
            cik, acc.replace("-", ""), doc)
        if out.get(url, {}).get("http_status") == "200":
            continue
        names = h.get("_source", {}).get("display_names") or [""]
        ok = _grab(url, "sec_fund_holding_filing",
                   "U.S. Securities and Exchange Commission, EDGAR",
                   "%s | %s | %s" % (h["_source"].get("file_date"),
                                     h["_source"].get("root_forms"), names[0]),
                   out, ua=SEC_UA,
                   local="sec_%s_%s" % (acc, _local_name(doc)))
        n += 1
        if not ok:
            print("    FAIL %s" % url[-60:])
    release_host("www.sec.gov", "EDGAR documents fetched")
    _write_manifest(out)
    print("  fetched %d EDGAR documents" % n)


# ===========================================================================
# STAGE 3 - parse.  A positional reader; the linear text layer lies.
# ===========================================================================
import fitz                                                  # noqa: E402

MONEY_RE = re.compile(r"^\(?-?\$?\s*(\d{1,3}(,\d{3})+|\d+)(\.\d{1,3})?\)?%?$")


def _is_num(t):
    t = t.strip()
    if t in {"-", "$-", "0", "$0"}:
        return True
    return bool(MONEY_RE.match(t)) and any(c.isdigit() for c in t)


def _num(t):
    t = t.strip()
    if t in {"-", "$-"}:
        return 0.0
    neg = (t.startswith("(") and t.endswith(")")) or t.startswith("-")
    v = float(re.sub(r"[^\d.]", "", t) or 0)
    return -v if neg else v


def page_lines(page, tol=3.5):
    """Words grouped into baselines, each word carrying its right edge."""
    words = page.get_text("words")
    rows = []
    for w in sorted(words, key=lambda w: (round(w[3], 1), w[0])):
        ym = (w[1] + w[3]) / 2.0
        item = dict(text=w[4], x0=w[0], x1=w[2], ym=ym)
        if rows and abs(ym - rows[-1]["ym"]) <= tol:
            rows[-1]["words"].append(item)
            rows[-1]["ym"] = (rows[-1]["ym"] * (len(rows[-1]["words"]) - 1)
                              + ym) / len(rows[-1]["words"])
        else:
            rows.append(dict(ym=ym, words=[item]))
    for r in rows:
        r["words"].sort(key=lambda w: w["x0"])
        r["text"] = re.sub(r"\s+", " ",
                           " ".join(w["text"] for w in r["words"])).strip()
    return rows


def band_columns(num_words, gap=18.0):
    """Cluster RIGHT edges. A right edge is stable across digit counts."""
    edges = sorted(w["x1"] for w in num_words)
    if not edges:
        return []
    bands, cur = [], [edges[0]]
    for e in edges[1:]:
        if e - cur[-1] > gap:
            bands.append(cur)
            cur = [e]
        else:
            cur.append(e)
    bands.append(cur)
    return [sum(b) / len(b) for b in bands]


def assign(w, centers):
    return min(range(len(centers)), key=lambda i: abs(w["x1"] - centers[i]))


# --- (A) Historical Indian Gaming Receipts ----------------------------------
FY_ROW = re.compile(r"^FY\s*(\d{4})/(\d{2})\b")
HIST_HDR = re.compile(r"Historical\s+Indian\s+Gaming\s+Receipts", re.I)
# Column order is fixed by the table's own printed headers, read left to right.
HIST_COLS = [
    "receipts_total_received",
    "receipts_general_revenue",
    "receipts_trust_fund",
    "receipts_reserve_within_gr",
    "receipts_excluding_banked_card_game_reserve",
    "receipts_release_of_reserve",
    "receipts_after_release_of_reserve",
    "receipts_local_distribution",
]
TOTAL_ROW = re.compile(r"^(Grand\s+)?(Running\s+Sub-)?Totals?\b", re.I)


def parse_hist_receipts(doc, meta):
    """The one table in the corpus that is ACTUAL money actually received.

    THE TABLE HAS TWO BLOCKS AND TWO PRINTED TOTALS. The 2007/2010-Compact
    years foot to `Total`; the 2021-Compact years foot to `Running Sub-Total`.
    Footing the whole table against either one fails by construction, which is
    exactly what the first pass did. Each block is therefore closed and footed
    at its own printed total row.

    Columns are banded over the DATA ROWS ONLY. Banding over the whole page
    pulled in the footnote figures ($2,916,666.67, $7,019,424) and the margin
    annotations (2007 Compact, 2010 Compact) and produced 14 columns for an
    8-column table.
    """
    rows, log = [], []
    for pno in range(doc.page_count):
        lines = page_lines(doc[pno])
        if not any(HIST_HDR.search(l["text"]) for l in lines):
            continue
        # pass 1: which lines are data or totals, so banding sees only them
        cand = []
        for l in lines:
            nums = [w for w in l["words"] if _is_num(w["text"])]
            if not nums:
                continue
            label = re.sub(r"\s+", " ", " ".join(
                w["text"] for w in l["words"] if not _is_num(w["text"]))).strip()
            m = FY_ROW.match(label)
            if m:
                cand.append(("data", m.group(1), m.group(2), l, nums))
            elif TOTAL_ROW.match(label):
                cand.append(("total", "", "", l, nums))
        if not any(c[0] == "data" for c in cand):
            continue
        centers = band_columns([w for c in cand for w in c[4]])
        if len(centers) < 3:
            continue
        # pass 2: close a block at every printed total row
        blocks, cur = [], []
        for kind, y1, y2, l, nums in cand:
            vals = [None] * len(centers)
            for w in nums:
                vals[assign(w, centers)] = _num(w["text"])
            if kind == "data":
                cur.append((y1, y2, vals, l["text"], pno + 1))
            else:
                blocks.append((cur, vals))
                cur = []
        if cur:
            blocks.append((cur, None))
        data = []
        for bi, (drows, tot) in enumerate(blocks):
            if not drows:
                continue
            ok, detail = True, []
            for i in range(len(centers)):
                s = round(sum((d[2][i] or 0) for d in drows), 2)
                p = tot[i] if tot else None
                if p is None:
                    detail.append("c%d:no_total" % i)
                    continue
                hit = abs(s - round(p, 2)) < 0.02
                ok = ok and hit
                detail.append("c%d:%.2f%s%.2f" % (i, s, "==" if hit else "!=", p))
            status = ("foots" if (ok and tot) else
                      ("no_total" if not tot else "foot_failed"))
            log.append(dict(file=meta["local_file"],
                            zone="historical_receipts_block%d" % bi,
                            status=status,
                            detail=("page=%d rows=%d cols=%d %s"
                                    % (pno + 1, len(drows), len(centers),
                                       "; ".join(detail)))[:400]))
            if status == "foot_failed":
                continue
            for d in drows:
                data.append((d, status, "; ".join(detail)))
        for (y1, y2, vals, quote, page), status, detail in data:
            fy_start = "%s-07-01" % y1
            fy_end = "%d-06-30" % (int(y1) + 1)
            for i, v in enumerate(vals):
                if v is None or i >= len(HIST_COLS):
                    continue
                rows.append(dict(
                    metric=HIST_COLS[i], value=v, value_as_published=v,
                    published_unit="USD",
                    period_start=fy_start, period_end=fy_end,
                    period_basis="state_fiscal_year",
                    period_label="FY %s/%s" % (y1, y2),
                    measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
                    is_forecast="no",
                    source_page=page, source_quote=quote[:400],
                    zone_header="Historical Indian Gaming Receipts (GR and Local)",
                    foot_status=status, foot_detail=detail[:300]))
    return rows, log


# --- (B) monthly actual collections ------------------------------------------
MONTHS = ["July", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar",
          "Apr", "May", "Jun"]
MONTH_NUM = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
SERIES_HDR = re.compile(
    r"^INDIAN\s+GAMING\s+(GR|TRUST\s+FUND|TOTAL\s+COLLECTIONS)\s*$", re.I)
ACTUAL_ROW = re.compile(r"^Actual\s+(\d{2})-(\d{2})\s*$", re.I)
SERIES_METRIC = {
    "GR": "monthly_collections_general_revenue",
    "TRUST FUND": "monthly_collections_trust_fund",
    "TOTAL COLLECTIONS": "monthly_collections_total",
}


def parse_monthly(doc, meta, conf_date):
    """Monthly actual collections, footed against the printed Year column.

    Values are printed in MILLIONS. They are normalised to USD in `value` and
    the published figure is kept beside it, because one column that silently
    mixes units is how a series becomes wrong without ever looking wrong.
    """
    rows, log = [], []
    for pno in range(doc.page_count):
        lines = page_lines(doc[pno])
        month_hdr = None
        series = None
        for l in lines:
            heads = [w["text"] for w in l["words"]]
            if heads[:3] == MONTHS[:3] and "Year" in heads:
                month_hdr = [w for w in l["words"]
                             if w["text"] in MONTHS + ["Year"]]
                continue
            m = SERIES_HDR.match(l["text"])
            if m:
                series = re.sub(r"\s+", " ", m.group(1).upper())
                continue
            am = ACTUAL_ROW.match(re.sub(
                r"\s*[\d.,\-]+\s*$", "", l["text"]).strip()) or ACTUAL_ROW.match(
                " ".join(w["text"] for w in l["words"][:2]))
            if not (am and month_hdr and series):
                continue
            nums = [w for w in l["words"] if _is_num(w["text"])]
            if len(nums) < 13:
                continue
            centers = [w["x1"] for w in month_hdr]
            vals = [None] * len(centers)
            for w in nums:
                vals[assign(w, centers)] = _num(w["text"])
            printed_year = vals[-1]
            s = round(sum(v for v in vals[:12] if v is not None), 1)
            # Each month is printed rounded to 0.1, so twelve of them can drift
            # up to 0.6 from a year total computed on unrounded figures. A
            # tighter tolerance rejects correct reads; a looser one would let a
            # mis-banded column through, and a mis-banded column is off by a
            # whole month, not by half a decimal.
            hit = printed_year is not None and abs(s - printed_year) <= 0.7
            status = "foots" if hit else "foot_failed"
            fy1 = 2000 + int(am.group(1))
            log.append(dict(file=meta["local_file"],
                            zone="monthly_%s" % SERIES_METRIC[series],
                            status=status,
                            detail="page=%d fy=%d-%s sum=%.1f printed=%s"
                                   % (pno + 1, fy1, am.group(2), s,
                                      printed_year)))
            if not hit:
                continue
            for i in range(12):
                if vals[i] is None:
                    continue
                mo = MONTH_NUM[i]
                yr = fy1 if mo >= 7 else fy1 + 1
                first = dt.date(yr, mo, 1)
                nxt = dt.date(yr + (mo == 12), (mo % 12) + 1, 1)
                last = nxt - dt.timedelta(days=1)
                future = bool(conf_date and first > conf_date)
                rows.append(dict(
                    metric=SERIES_METRIC[series],
                    value=round(vals[i] * 1e6, 2),
                    value_as_published=vals[i],
                    published_unit="USD millions",
                    period_start=first.isoformat(),
                    period_end=last.isoformat(),
                    period_basis="month",
                    period_label="%s FY%d-%s" % (MONTHS[i], fy1, am.group(2)),
                    measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
                    is_forecast="no",
                    source_page=pno + 1, source_quote=l["text"][:400],
                    zone_header="YEAR-TO-DATE PERFORMANCE - INDIAN GAMING %s"
                                % series,
                    foot_status=status,
                    foot_detail="sum=%.1f printed=%s" % (s, printed_year),
                    exclusion_flag=("month_after_conference_date_not_yet_"
                                    "occurred" if future else ""),
                    exclusion_reason=(
                        "Printed as 0.0 in an in-progress fiscal year. The "
                        "month falls after the conference date, so the zero is "
                        "an empty cell, not a measured zero."
                        if future else "")))
    return rows, log


# --- (B2) the pre-2024 monthly receipts blocks -------------------------------
# Before EDR moved to the single year-to-date grid, each conference printed a
# fiscal-year block per page position: `Mon-YY | Receipts | Local Distribution
# [| True-up Payment]`, side by side, and TWICE - once for the prior forecast
# vintage and once for the adopted one. Column identity is read from the
# printed header words, never from position alone, and every column is footed
# against the block's own printed fiscal-year total row. A column that does not
# foot is not published.
MON_TOK = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
                     r"-(\d{2})$")
FYTOT_TOK = re.compile(r"^(\d{4})-(\d{2})$")
HDR_WORDS = {"Receipts", "Distribution", "Payment"}


def parse_monthly_blocks(doc, meta, conf_date=None):
    rows, log = [], []
    for pno in range(doc.page_count):
        lines = page_lines(doc[pno], tol=2.5)
        i = 0
        while i < len(lines):
            hdr = [w for w in lines[i]["words"] if w["text"] in HDR_WORDS]
            if len([w for w in hdr if w["text"] == "Receipts"]) < 1 or \
                    len(hdr) < 2:
                i += 1
                continue
            centers = [w["x1"] for w in hdr]
            names = [w["text"] for w in hdr]
            months, total_line = [], None
            j = i + 1
            while j < len(lines) and total_line is None:
                ws = lines[j]["words"]
                labs = [w for w in ws if MON_TOK.match(w["text"])]
                fyl = [w for w in ws if FYTOT_TOK.match(w["text"])]
                nums = [w for w in ws if _is_num(w["text"])]
                if labs and nums:
                    months.append((labs, nums, lines[j]))
                elif fyl and nums:
                    total_line = (fyl, nums, lines[j])
                elif len(months) > 3 and not nums:
                    break
                j += 1
            i = j + 1
            if total_line is None or len(months) < 6:
                continue
            fyl, tnums, tline = total_line
            tvals = [None] * len(centers)
            for w in tnums:
                tvals[assign(w, centers)] = _num(w["text"])
            # a column belongs to the fiscal-year block whose label sits to its
            # left; the labels are printed on the total row
            fyl = sorted(fyl, key=lambda w: w["x0"])
            colfy = []
            for c in centers:
                lab = [w for w in fyl if w["x0"] < c]
                colfy.append(FYTOT_TOK.match(lab[-1]["text"]).groups()
                             if lab else None)
            colvals = defaultdict(dict)
            quotes = {}
            for labs, nums, ln in months:
                mv = [None] * len(centers)
                for w in nums:
                    mv[assign(w, centers)] = _num(w["text"])
                labs = sorted(labs, key=lambda w: w["x0"])
                for k in range(len(centers)):
                    left = [w for w in labs if w["x0"] < centers[k]]
                    if not left:
                        continue
                    mm = MON_TOK.match(left[-1]["text"])
                    colvals[k][mm.group(0)] = mv[k]
                    quotes[(k, mm.group(0))] = ln["text"][:400]
            for k in range(len(centers)):
                if names[k] != "Receipts" or colfy[k] is None:
                    continue
                vals = {m: v for m, v in colvals[k].items() if v is not None}
                if len(vals) < 10 or tvals[k] is None:
                    continue
                s = round(sum(vals.values()), 2)
                if abs(s - tvals[k]) > 0.06:
                    log.append(dict(file=meta["local_file"],
                                    zone="monthly_block_receipts",
                                    status="foot_failed",
                                    detail="page=%d fy=%s-%s col=%d sum=%.2f "
                                           "printed=%.2f"
                                           % (pno + 1, colfy[k][0], colfy[k][1],
                                              k, s, tvals[k])))
                    continue
                log.append(dict(file=meta["local_file"],
                                zone="monthly_block_receipts", status="foots",
                                detail="page=%d fy=%s-%s col=%d months=%d "
                                       "sum=%.2f"
                                       % (pno + 1, colfy[k][0], colfy[k][1], k,
                                          len(vals), s)))
                for mon, v in vals.items():
                    mm = MON_TOK.match(mon)
                    mo = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
                          "Aug", "Sep", "Oct", "Nov", "Dec"].index(
                        mm.group(1)) + 1
                    yr = 2000 + int(mm.group(2))
                    first = dt.date(yr, mo, 1)
                    nxt = dt.date(yr + (mo == 12), (mo % 12) + 1, 1)
                    # A block runs from closed months into forecast months
                    # without changing shape. EDR can only report an actual for
                    # a month that has happened, so the conference's own date
                    # is the line between the two - and it is the ONLY thing in
                    # the document that draws it.
                    fut = bool(conf_date and first > conf_date)
                    rows.append(dict(
                        metric="monthly_collections_total",
                        value=round(v * 1e6, 2), value_as_published=v,
                        published_unit="USD millions",
                        period_start=first.isoformat(),
                        period_end=(nxt - dt.timedelta(days=1)).isoformat(),
                        period_basis="month", period_label=mon,
                        measurement_type=(
                            MeasurementType.PROJECTED.value if fut else
                            MeasurementType.REGULATORY_REPORTED_COUNT.value),
                        is_forecast="yes" if fut else "no",
                        exclusion_flag=("state_forecast_not_an_observation"
                                        if fut else ""),
                        exclusion_reason=(
                            "The month falls after this conference's own date, "
                            "so the figure is the conference's forecast of a "
                            "payment not yet made." if fut else ""),
                        source_page=pno + 1,
                        source_quote=quotes.get((k, mon), "")[:400],
                        zone_header="Monthly Receipts / Local Distribution, "
                                    "fiscal year %s-%s"
                                    % (colfy[k][0], colfy[k][1]),
                        foot_status="foots",
                        foot_detail="sum=%.2f==printed %.2f" % (s, tvals[k])))
    return rows, log


# --- (B3) the 2010-Compact Net Win series ------------------------------------
# EDR's December 2015 conference states its own source in the document:
#   "the actual Net Win for Fiscal Year 2014-15, and other information from the
#    most recent quarterly financial reports available from the Tribe"
# so for a fiscal year that CLOSED before the conference met, the Net Win in
# this table is the State's statement of a figure the Tribe reported to it -
# TRIBE_LEVEL_REVENUE, revenue concept "Net Win" as the compact defines it. For
# a fiscal year that had not closed, the same column is a forecast.
#
# The table is sparse and its columns move between vintages, so the columns are
# NOT identified by position. They are identified by CONTENT: the 2010 Compact
# schedule is a strictly monotone piecewise-linear function, so a (base,
# obligation) pair either satisfies it to the cent or it does not. Exactly one
# qualifying pair per row is required; anything else is refused and logged.
FY_LABEL = re.compile(r"^(\d{4})-(\d{2})$")
BANDS_2010 = [(2000.0, 0.12), (1000.0, 0.15), (500.0, 0.175), (500.0, 0.20),
              (500.0, 0.225), (float("inf"), 0.25)]


def schedule_2010(net_win_millions):
    """The 2010 Compact's Percentage Revenue Share Amount, in $m."""
    rem, out = net_win_millions, 0.0
    for width, rate in BANDS_2010:
        take = min(rem, width)
        out += take * rate
        rem -= take
        if rem <= 0:
            break
    return out


def parse_netwin_actual(doc, meta, conf_date=None):
    rows, log = [], []
    for pno in range(doc.page_count):
        lines = page_lines(doc[pno], tol=2.5)
        if not any(re.search(r"Revenues\s*$|Net\s*$", l["text"]) for l in lines):
            pass
        for l in lines:
            ws = l["words"]
            if not ws:
                continue
            m = FY_LABEL.match(ws[0]["text"])
            if not m:
                continue
            nums = [_num(w["text"]) for w in ws[1:]
                    if _is_num(w["text"]) and not w["text"].endswith("%")
                    and not w["text"].startswith("(")]
            nums = [v for v in nums if v > 0]
            if len(nums) < 2:
                continue
            hits = []
            for a in nums:
                if a < 300:
                    continue
                for b in nums:
                    if b >= a or not (0.10 <= b / a <= 0.26):
                        continue
                    if abs(schedule_2010(a) - b) <= 0.15:
                        hits.append((a, b))
            hits = sorted(set(hits))
            fy1 = int(m.group(1))
            fy_end = dt.date(fy1 + 1, 6, 30)
            if len(hits) != 1:
                log.append(dict(file=meta["local_file"], zone="netwin_actual",
                                status=("schedule_unmatched" if not hits
                                        else "schedule_ambiguous"),
                                detail="page=%d fy=%s-%s nums=%s"
                                       % (pno + 1, m.group(1), m.group(2),
                                          nums[:8])))
                continue
            a, b = hits[0]
            closed = bool(conf_date and fy_end < conf_date)
            log.append(dict(file=meta["local_file"], zone="netwin_actual",
                            status="foots",
                            detail="page=%d fy=%s-%s net_win=%.1f obligation="
                                   "%.1f closed=%s"
                                   % (pno + 1, m.group(1), m.group(2), a, b,
                                      closed)))
            base = dict(
                period_start="%d-07-01" % fy1,
                period_end=fy_end.isoformat(),
                period_basis="revenue_sharing_cycle_as_labelled_by_edr",
                period_label="%s-%s" % (m.group(1), m.group(2)),
                measurement_type=(
                    MeasurementType.REGULATORY_REPORTED_COUNT.value if closed
                    else MeasurementType.PROJECTED.value),
                is_forecast="no" if closed else "yes",
                source_page=pno + 1, source_quote=l["text"][:400],
                zone_header="Net Win, Net Revenues and True-up Payment by "
                            "Fiscal Year (2010 Compact schedule)",
                foot_status="foots",
                foot_detail=("the 2010 Compact schedule applied to %.1f "
                             "reproduces the printed obligation %.1f" % (a, b)),
                exclusion_flag=("" if closed
                                else "state_forecast_not_an_observation"),
                exclusion_reason=("" if closed else
                                  "The fiscal year had not closed when the "
                                  "conference met, so the figure is a "
                                  "forecast."))
            rows.append(dict(base, metric="net_win_subject_to_revenue_share",
                             value=round(a * 1e6, 2), value_as_published=a,
                             published_unit="USD millions"))
            rows.append(dict(base,
                             metric="revenue_share_obligation_for_cycle",
                             value=round(b * 1e6, 2), value_as_published=b,
                             published_unit="USD millions"))
            # The leftmost data column of this table is total Net Win; the
            # footed base is `Remaining Net Win`, which in FY2015-16 and
            # FY2016-17 is total Net Win less the table-game revenue the
            # State excluded from the share base while the banked card game
            # authorisation had lapsed. The two are different facts and the
            # difference is the whole story of those two years, so both are
            # recorded and neither is called the other.
            if nums and a <= nums[0] <= a * 3:
                rows.append(dict(
                    base, metric="net_win_total",
                    value=round(nums[0] * 1e6, 2), value_as_published=nums[0],
                    published_unit="USD millions",
                    foot_detail=base["foot_detail"] + "; total Net Win read "
                                "from the leftmost data column and required to "
                                "be at least the footed share base"))
    return rows, log


# --- (C) forecast Net Win / revenue share by game category -------------------
CYCLE_ROW = re.compile(r"^(\d{4})-(\d{2})$")
CAT_TITLES = [
    (re.compile(r"Revenue\s+Sharing\s+for\s+Slot\s+Machines", re.I),
     "slot_machines"),
    (re.compile(r"Revenue\s+Sharing\s+for\s+Table\s+Games", re.I),
     "table_games"),
    (re.compile(r"Revenue\s+Sharing\s+for\s+Sports\s+Betting", re.I),
     "sports_betting"),
    (re.compile(r"Qualified\s+Pari-?mutuel\s+Permitholder", re.I),
     "sports_betting_qualified_permitholder_brand"),
    (re.compile(r"Total\s+Net\s+Win\s+and\s+Revenue\s+Sharing", re.I),
     "all_covered_games"),
    (re.compile(r"Total\s+Revenue\s+Share", re.I), "all_covered_games"),
]


def parse_netwin_forecast(doc, meta):
    """EDR's forecast of Net Win and revenue share, by game category.

    THIS IS A STATE FORECAST, NOT A TRIBAL REPORT. It is recorded as PROJECTED
    with revenue_evidence_class NO_REVENUE_OBSERVATION. Every block must foot
    against its own printed effective rate (rev_share / net_win) or it is
    refused - which is also what proves the two money columns were read into
    the right order.
    """
    rows, log = [], []
    for pno in range(doc.page_count):
        lines = page_lines(doc[pno])
        titles = []
        for l in lines:
            for pat, cat in CAT_TITLES:
                if pat.search(l["text"]):
                    titles.append((l["ym"], cat, l["text"]))
        if not titles:
            continue
        blocks = defaultdict(list)
        for l in lines:
            ws = l["words"]
            if not ws:
                continue
            lab = ws[0]["text"]
            m = CYCLE_ROW.match(lab)
            if not m:
                continue
            nums = [w for w in ws[1:] if _is_num(w["text"])]
            if len(nums) != 4:
                continue
            v = [_num(w["text"]) for w in nums]
            net, growth, share, eff = v
            if net <= 0:
                continue
            # the block's own consistency test
            if abs(share / net * 100.0 - eff) > 0.06:
                continue
            above = [t for t in titles if t[0] < l["ym"]]
            cat = above[-1][1] if above else ""
            hdr = above[-1][2] if above else ""
            if not cat:
                continue
            blocks[(cat, hdr)].append((m.group(1), m.group(2), net, share,
                                       eff, l["text"], pno + 1))
        for (cat, hdr), recs in blocks.items():
            log.append(dict(file=meta["local_file"],
                            zone="netwin_forecast_%s" % cat, status="foots",
                            detail="page=%d rows=%d" % (pno + 1, len(recs))))
            for y1, y2, net, share, eff, quote, page in recs:
                # The Revenue Sharing Cycle is a 12-month period the compact
                # defines; EDR labels it by the state fiscal year it maps to.
                base = dict(
                    period_start="%s-07-01" % y1,
                    period_end="%d-06-30" % (int(y1) + 1),
                    period_basis="revenue_sharing_cycle_as_labelled_by_edr",
                    period_label="%s-%s cycle" % (y1, y2),
                    measurement_type=MeasurementType.PROJECTED.value,
                    is_forecast="yes",
                    source_page=page, source_quote=quote[:400],
                    zone_header=hdr[:300], foot_status="foots",
                    foot_detail="rev_share/net_win==printed_effective_rate",
                    exclusion_flag="state_forecast_not_an_observation",
                    exclusion_reason=(
                        "Adopted forecast of the Revenue Estimating "
                        "Conference. EDR estimates Net Win in order to "
                        "forecast the payment; the Tribe does not publish Net "
                        "Win and the compact marks what it gives the State "
                        "confidential. Never read as a reported revenue."))
                rows.append(dict(base, metric="forecast_net_win_%s" % cat,
                                 value=round(net * 1e6, 2),
                                 value_as_published=net,
                                 published_unit="USD millions"))
                rows.append(dict(base,
                                 metric="forecast_revenue_share_%s" % cat,
                                 value=round(share * 1e6, 2),
                                 value_as_published=share,
                                 published_unit="USD millions"))
                rows.append(dict(base,
                                 metric="forecast_effective_share_rate_%s" % cat,
                                 value=eff, value_as_published=eff,
                                 published_unit="percent"))
    return rows, log


CONF_DATE = re.compile(r"(\d{2})(\d{2})(\d{2})IndianGaming", re.I)
MONTH_NAMES = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}
IN_DOC_DATE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2}),\s*(\d{4})")


def _conference_date(local_file, doc):
    """The archive names the file by conference date; the CURRENT conference is
    served from an unversioned filename, so fall back to the date the document
    prints on itself. A conference date is what orders the restatements."""
    cm = CONF_DATE.search(local_file)
    if cm:
        try:
            return dt.date(2000 + int(cm.group(1)), int(cm.group(2)),
                           int(cm.group(3)))
        except ValueError:
            pass
    if doc.page_count:
        m = IN_DOC_DATE.search(doc[0].get_text()[:2500])
        if m:
            try:
                return dt.date(int(m.group(3)), MONTH_NAMES[m.group(1)],
                               int(m.group(2)))
            except ValueError:
                pass
    return None


def parse_edr():
    rows, log = [], []
    for m in _manifest_rows("edr_indian_gaming_conference"):
        path = os.path.join(RAW, m["local_file"])
        try:
            doc = fitz.open(path)
        except Exception as e:
            log.append(dict(file=m["local_file"], zone="", status="unreadable",
                            detail=str(e)[:150]))
            continue
        cd = _conference_date(m["local_file"], doc)
        got = 0
        for fn in (parse_hist_receipts, parse_monthly, parse_monthly_blocks,
                   parse_netwin_actual, parse_netwin_forecast):
            try:
                r, l = (fn(doc, m, cd)
                        if fn in (parse_monthly, parse_monthly_blocks,
                                  parse_netwin_actual)
                        else fn(doc, m))
            except Exception as e:
                log.append(dict(file=m["local_file"], zone=fn.__name__,
                                status="parse_error", detail=str(e)[:180]))
                continue
            for x in r:
                x["source_file"] = m["local_file"]
                x["source_url"] = m["source_url"]
                x["source_document_type"] = "edr_revenue_estimating_conference"
                x["source_authority"] = m["source_authority"]
                x["source_link_text"] = m["doc_label"]
                x["fetched_date"] = m["fetched_date"]
                x["conference_date"] = cd.isoformat() if cd else ""
            rows += r
            log += l
            got += len(r)
        if not got:
            log.append(dict(file=m["local_file"], zone="", status="no_zone",
                            detail="no recognised Indian Gaming table"))
        doc.close()
    return rows, log


# ===========================================================================
# supersession - EDR restates the same period across conferences
# ===========================================================================
def apply_supersession(rows):
    """Keep every conference's statement; flag all but the latest as restated.

    EDR republishes the same fiscal year at every conference. Summing across
    documents would multiply the series by 39. The newest conference date wins;
    everything earlier is kept, readable, and flagged.
    """
    best = {}
    for r in rows:
        k = (r["metric"], r["period_start"], r["period_end"])
        d = r.get("conference_date") or ""
        if k not in best or d > best[k]:
            best[k] = d
    n = 0
    for r in rows:
        k = (r["metric"], r["period_start"], r["period_end"])
        if (r.get("conference_date") or "") < best[k]:
            r["exclusion_flag"] = r.get("exclusion_flag") or \
                "restated_by_later_conference"
            r["exclusion_reason"] = r.get("exclusion_reason") or (
                "A later Revenue Estimating Conference published the same "
                "period. Retained as the conference's statement at the time; "
                "excluded from any single-value series.")
            n += 1
        else:
            r["document_status"] = "latest_statement_for_period"
    return n


# ===========================================================================
# the governing compact, and the bound its schedule supports
# ===========================================================================
COMPACT_PDF_TEXT = os.path.join(ROOT, "data", "raw", "external", "compacts",
                                "text")

# Read from the instrument text, quoted verbatim below and re-verified at run
# time against the local compact text. Rate_min is the LOWEST marginal rate in
# the governing instrument across every game category, which is what makes
# `Net Win <= payment / rate_min` exact rather than approximate.
COMPACT_SCHEDULE = [
    dict(compact_id="CMP-FL-seminole-tribe-of-florida-20100706",
         effective_from="2010-07-06", effective_to="2021-08-10",
         rate_min=12.0, rate_max=25.0,
         schedule="12% / 15% / 17.5% / 20% / 22.5% / 25% of Net Win from "
                  "Covered Games, by band",
         revenue_concept="Net Win from Covered Games",
         base_scope="tribe",
         guaranteed_minimum="Guaranteed Minimum Revenue Sharing Cycle Payment "
                            "for the first three Revenue Sharing Cycles",
         text_file="508_compliant_2010.07.06_seminole_tribe_tribal_state_"
                   "gaming_compact.txt",
         probe="Twelve percent (12%) of all amounts up to Two Billion",
         url="https://www.bia.gov/sites/default/files/dup/assets/as-ia/oig/pdf/"
             "508_compliant_2010.07.06_seminole_tribe_tribal_state_gaming_"
             "compact.pdf"),
    dict(compact_id="CMP-FL-seminole-tribe-of-florida-20210811",
         effective_from="2021-08-11", effective_to="2051-07-31",
         rate_min=10.0, rate_max=25.0,
         schedule="Slot Machines 12%-25%; Table Games 15%-25%; Sports Betting "
                  "13.75%; Sports Betting via a Qualified Pari-mutuel "
                  "Permitholder brand 10% - all of Net Win, by band",
         revenue_concept="Net Win",
         base_scope="tribe",
         guaranteed_minimum="$1.5bn by the end of the 3rd cycle, $2.5bn by the "
                            "end of the 5th cycle, and not less than $400m for "
                            "any cycle in the first five years",
         text_file="508 Compliant 2021.08.11 Seminole Tribe Gaming Compact.txt",
         probe="Ten percent (10%) of Net Win received by the Tribe from the",
         url="https://www.bia.gov/sites/default/files/dup/assets/as-ia/oig/pdf/"
             "508%20Compliant%202021.08.11%20Seminole%20Tribe%20Gaming%20"
             "Compact.pdf"),
]
# The 2007 compact ran 2008-01-07 to 2010-07-05 and is what the FY2007/08 and
# FY2008/09 receipts fall under. Its payment terms are stated GUARANTEED
# amounts, not a percentage of anything, so no bound is derivable at all.
PRE2010 = dict(compact_id="CMP-FL-seminole-tribe-of-florida-20080107",
               effective_from="2008-01-07", effective_to="2010-07-05")


def verify_compact_quotes(log):
    """Re-read the instrument before trusting the schedule encoded above."""
    for c in COMPACT_SCHEDULE:
        p = os.path.join(COMPACT_PDF_TEXT, c["text_file"])
        c["verified"] = "no"
        c["quote"] = ""
        if not os.path.exists(p):
            log.append(dict(file=c["text_file"], zone="compact_schedule",
                            status="missing_local_text", detail=c["compact_id"]))
            continue
        t = open(p, encoding="utf-8", errors="replace").read()
        i = t.find(c["probe"])
        if i < 0:
            log.append(dict(file=c["text_file"], zone="compact_schedule",
                            status="probe_not_found", detail=c["probe"][:80]))
            continue
        c["verified"] = "yes"
        c["quote"] = re.sub(r"\s+", " ", t[i:i + 380]).strip()
        log.append(dict(file=c["text_file"], zone="compact_schedule",
                        status="verified", detail=c["compact_id"]))
    return [c for c in COMPACT_SCHEDULE if c["verified"] == "yes"]


def governing(schedules, period_end):
    for c in schedules:
        if c["effective_from"] <= period_end <= c["effective_to"]:
            return c
    return None


# ===========================================================================
# entity resolution - one resolver, plus refusals
# ===========================================================================
SPINE_PATH = os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv")
FACILITIES = os.path.join(CLEAN, "gaming_facilities.csv")


def load_spine_view():
    spine = _read(SPINE_PATH)
    for r in spine:
        extra = [r.get("fr_official_name", "")]
        r["aliases"] = "|".join([a for a in ([r.get("aliases", "")] + extra)
                                 if a and a.strip()])
    return spine


class TribeResolver:
    """Resolve a published Florida name, then refuse anything not in Florida.

    The state guard is the whole point. `Seminole` resolves to the Florida
    tribe and `The Seminole Nation of Oklahoma` to a different spine entity in
    a different state; a Florida gaming payment can only be the former, and a
    build that let the latter through would repeat a misattribution this repo
    has already made once across this exact pair.
    """

    def __init__(self):
        self.spine = load_spine_view()
        self.by_id = {r["tribe_id"]: r for r in self.spine}
        self.cache, self.reasons = {}, Counter()

    def resolve(self, raw):
        name = re.sub(r"\s+", " ", (raw or "")).strip()
        if name in self.cache:
            return self.cache[name]
        tid, canon, how = resolve_entity(name, self.spine)
        res = dict(tribe_id="", tribe_canonical_name="", match_method=how,
                   entity_tier="", refusal="")
        if not tid:
            res["refusal"] = how
        else:
            ent = self.by_id[tid]
            cls = ent.get("entity_class", "")
            st = (ent.get("state") or "").strip()
            if cls in REFUSED_ENTITY_CLASSES:
                res["refusal"] = "refused_entity_class:%s" % cls
            elif st not in ALLOWED_STATES:
                res["refusal"] = "refused_cross_state:%s" % st
            else:
                res.update(tribe_id=tid,
                           tribe_canonical_name=ent["canonical_name"],
                           entity_tier=Tier.B.value)
        self.reasons[(res["refusal"] or ("resolved_" + how)).split(":")[0]] += 1
        self.cache[name] = res
        return res


# ===========================================================================
# STAGE 4 - emit
# ===========================================================================
PAY_FIELDS = [
    "payment_id", "state", "fund", "direction", "recipient_type",
    "tribe_id", "tribe_canonical_name", "party_name_as_published",
    "facility_id", "facility_name",
    "metric", "value", "unit", "value_as_published", "published_unit",
    "period_start", "period_end", "period_basis", "period_label",
    "conference_date", "measurement_type", "is_forecast",
    "revenue_evidence_class",
    "governing_compact_id", "compact_rate_schedule",
    "compact_rate_min_pct", "compact_rate_max_pct",
    "compact_revenue_concept", "compact_base_scope",
    "compact_guaranteed_minimum", "payment_invertible",
    "derived_revenue_bound_value", "derived_bound_direction",
    "derived_revenue_scope", "bound_basis",
    "compact_term_source_url", "compact_term_source_quote",
    "confidence_tier", "entity_match_method", "entity_tier",
    "exclusion_flag", "exclusion_reason",
    "source_authority", "source_document_type", "source_url", "source_page",
    "source_quote", "source_link_text", "zone_header",
    "foot_status", "foot_detail", "document_status",
    "fetched_date", "built_date", "built_by_script",
]

BOND_FIELDS = [
    "disclosure_id", "tribe_id", "tribe_canonical_name",
    "obligor_name_as_published", "conduit_issuer_as_published",
    "disclosure_class", "security_description", "series", "coupon_pct",
    "maturity_date", "amount_usd", "amount_concept",
    "rating", "rating_agency",
    "filer_name", "filer_cik", "filing_form", "filing_date",
    "fiscal_year", "period_end",
    "availability_status", "availability_basis",
    "carries_gaming_revenue", "revenue_evidence_class", "measurement_type",
    "confidence_tier", "entity_match_method", "entity_tier",
    "source_authority", "source_document_type", "source_url", "source_page",
    "source_quote", "fetched_date", "built_date", "built_by_script",
]

REVIEW_FIELDS = [
    "review_id", "issue_type", "name_as_published", "context", "evidence",
    "question", "candidate_entities", "source_url", "source_quote",
    "YOUR_RULING",
]


# --- bond / audited-disclosure layer -----------------------------------------
# The conduit issuer is bounded to a plausible issuer name that ENDS in an
# issuer word. An unbounded leading group swallowed the whole preceding table
# cell ("...Municipal Income Fund Security Acquisition Date Acquisition Cost
# Capital Trust Agency") and put a fund's column headers in an issuer field.
BOND_LINE = re.compile(
    r"((?:[A-Z][A-Za-z.'&\-]+\s+){1,5}"
    r"(?:Agency|Authority|Corporation|Board|District|Commission|County))"
    r"(?:,?\s*(?:FL|Florida))?,?\s*"
    r"(?:Revenue\s+)?Bonds?[^,()]{0,40}?"
    r"\(Series\s+([0-9]{4}[A-Z]?)\),?\s*"
    r"([0-9]{1,2}\.[0-9]{2,3})\s*%\s*"
    r"\(Seminole\s+Tribe\s+of\s+Florida([^)]*)\),?\s*"
    r"([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})")

# The other instrument class in the same filings, and one the municipal
# pattern cannot see: the Tribe's 2007-vintage senior secured TERM LOAN, held
# in tranches by registered loan funds. `tribal_bond_issuances.csv` records the
# facility at $794m maturing 2014; these filings name the tranches.
# No maturity is required. These lines are torn across a fund table's columns
# ("Term B-2 Delay, 7.125%, 3/5$ 282,"), so the date is often truncated to
# nothing usable. The tranche and its rate survive intact and are the content;
# inventing the year from a fragment would be the fabrication this file exists
# to avoid.
TERM_LOAN_LINE = re.compile(
    r"Seminole\s+Tribe\s+of\s+Florida,\s*"
    r"(Term\s+B[- ]?[12][A-Za-z ]{0,26}?)\s*,?\s*"
    r"([0-9]{1,2}\.[0-9]{1,3})\s*%?")


def parse_sec_holdings(tr, review):
    """Registered fund holdings that NAME a Seminole Tribe bond.

    A fund's schedule of investments is a filed, dated, primary SEC disclosure.
    It is not the Tribe's disclosure and carries no revenue: what it carries is
    the SECURITY - conduit issuer, series, coupon, maturity - which is how the
    2001 and 2003A Capital Trust Agency conduit issues surface at all. They are
    not in `tribal_bond_issuances.csv`, whose Seminole rows start at 2005A.
    """
    out, best = [], {}
    res = tr.resolve("Seminole Tribe of Florida")
    for m in _manifest_rows("sec_fund_holding_filing"):
        p = os.path.join(RAW, m["local_file"])
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        t = re.sub(r"<[^>]+>", " ", t)
        t = html.unescape(t)
        flat = re.sub(r"\s+", " ", t)
        for mm in TERM_LOAN_LINE.finditer(flat):
            tranche = re.sub(r"\s+", " ", mm.group(1)).strip(" ,")
            coupon = mm.group(2)
            if float(coupon) > 20:          # a par amount, not a rate
                continue
            key = ("loan", tranche.lower()[:14], coupon)
            if key in best:
                continue
            best[key] = dict(
                tribe_id=res["tribe_id"],
                tribe_canonical_name=res["tribe_canonical_name"],
                obligor_name_as_published="Seminole Tribe of Florida",
                conduit_issuer_as_published="",
                disclosure_class="term_loan_named_in_registered_fund_holding",
                security_description=re.sub(r"\s+", " ",
                                            mm.group(0)).strip()[:300],
                series=tranche, coupon_pct=coupon,
                maturity_date="",
                amount_usd="", amount_concept="",
                filer_name=(m["doc_label"].split("|")[2].strip()
                            if m["doc_label"].count("|") >= 2
                            else m["doc_label"]),
                filer_cik="",
                filing_form=re.sub(r"[\[\]']", "",
                                   m["doc_label"].split("|")[1]).strip()
                            if "|" in m["doc_label"] else "",
                filing_date=(m["doc_label"].split("|")[0].strip()
                             if "|" in m["doc_label"] else ""),
                availability_status="retrieved",
                availability_basis="EDGAR is a public repository and the "
                                   "document was retrieved in full",
                carries_gaming_revenue="no",
                revenue_evidence_class="NO_REVENUE_OBSERVATION",
                measurement_type="",
                entity_match_method=res["match_method"],
                entity_tier=res["entity_tier"],
                source_authority=m["source_authority"],
                source_document_type=(
                    "sec_registered_fund_schedule_of_investments"),
                source_url=m["source_url"], source_page="",
                source_quote=re.sub(r"\s+", " ", mm.group(0)).strip()[:400],
                fetched_date=m["fetched_date"])
        for mm in BOND_LINE.finditer(flat):
            conduit = mm.group(1).strip(" ,")
            series, coupon = mm.group(2), mm.group(3)
            purpose = re.sub(r"\s+", " ", mm.group(4)).strip(" ,")
            mat = mm.group(5)
            # The security IS (series, coupon, maturity). The issuer name is
            # what the leading regex group happened to reach, so the SHORTEST
            # reading of it wins - a longer one has run back into the previous
            # table cell.
            key = ("bond", series, coupon, mat)
            if key in best and len(best[key]["conduit_issuer_as_published"]) \
                    <= len(conduit):
                continue
            mo, d, y = mat.split("/")
            best[key] = dict(
                tribe_id=res["tribe_id"],
                tribe_canonical_name=res["tribe_canonical_name"],
                obligor_name_as_published="Seminole Tribe of Florida"
                                          + ((" " + purpose) if purpose else ""),
                conduit_issuer_as_published=conduit,
                disclosure_class="bond_named_in_registered_fund_holding",
                security_description=re.sub(r"\s+", " ",
                                            mm.group(0)).strip()[:300],
                series=series, coupon_pct=coupon,
                maturity_date="%s-%02d-%02d" % (y, int(mo), int(d)),
                amount_usd="", amount_concept="",
                filer_name=(m["doc_label"].split("|")[2].strip()
                            if m["doc_label"].count("|") >= 2
                            else m["doc_label"]),
                filer_cik="",
                filing_form=re.sub(r"[\[\]']", "",
                                   m["doc_label"].split("|")[1]).strip()
                            if "|" in m["doc_label"] else "",
                filing_date=(m["doc_label"].split("|")[0].strip()
                             if "|" in m["doc_label"] else ""),
                availability_status="retrieved",
                availability_basis="EDGAR is a public repository and the "
                                   "document was retrieved in full",
                carries_gaming_revenue="no",
                revenue_evidence_class="NO_REVENUE_OBSERVATION",
                measurement_type="",
                entity_match_method=res["match_method"],
                entity_tier=res["entity_tier"],
                source_authority=m["source_authority"],
                source_document_type="sec_registered_fund_schedule_of_investments",
                source_url=m["source_url"], source_page="",
                source_quote=re.sub(r"\s+", " ", mm.group(0)).strip()[:400],
                fetched_date=m["fetched_date"])
    out.extend(best.values())
    return out


FAC_QUOTE = (
    'is_public: false. 2 CFR 200.512(b)(2): "The FAC is responsible for '
    'making the reporting package ... available for public inspection ... '
    'However, the FAC must not make available reporting packages of Indian '
    'Tribes and Tribal organizations unless the Indian Tribe or Tribal '
    'organization has opted in to authorize the FAC to make the reporting '
    'package publicly available."')


def parse_fac(tr):
    """The audited statements exist, are filed, and are withheld by rule."""
    p = os.path.join(RAW, "fac_seminole_tribe_of_florida.json")
    if not os.path.exists(p):
        return []
    recs = json.load(open(p, encoding="utf-8"))
    out = []
    for r in recs:
        if (r.get("auditee_state") or "FL") != "FL":
            continue
        res = tr.resolve(r.get("auditee_name") or "")
        pub = bool(r.get("is_public"))
        out.append(dict(
            tribe_id=res["tribe_id"],
            tribe_canonical_name=res["tribe_canonical_name"],
            obligor_name_as_published=r.get("auditee_name", ""),
            conduit_issuer_as_published="",
            disclosure_class="single_audit_reporting_package",
            security_description="",
            series="", coupon_pct="", maturity_date="",
            amount_usd=r.get("total_amount_expended", ""),
            amount_concept="total federal awards expended (NOT revenue, NOT "
                           "gaming; the Single Audit threshold measure)",
            rating="", rating_agency="",
            filer_name=r.get("auditor_firm_name", ""), filer_cik="",
            filing_form="Single Audit (2 CFR 200 Subpart F)",
            filing_date=r.get("fac_accepted_date", ""),
            fiscal_year=r.get("audit_year", ""),
            period_end=r.get("fy_end_date", ""),
            availability_status="public" if pub else "withheld_by_rule",
            availability_basis=("" if pub else FAC_QUOTE),
            carries_gaming_revenue="unknown_document_not_available"
                                   if not pub else "unknown",
            revenue_evidence_class="NO_REVENUE_OBSERVATION",
            measurement_type="",
            entity_match_method=res["match_method"],
            entity_tier=res["entity_tier"],
            source_authority="Federal Audit Clearinghouse (GSA)",
            source_document_type="fac_dissemination_general_record",
            source_url="https://api.fac.gov/general?auditee_ein=eq.591415030",
            source_page="",
            source_quote=("report_id=%s audit_year=%s auditor=%s is_public=%s"
                          % (r.get("report_id"), r.get("audit_year"),
                             r.get("auditor_firm_name"), r.get("is_public"))),
            fetched_date=TODAY))
    return out


def emma_row(tr):
    """EMMA holds the official statements. Its robots.txt disallows the PDFs.

    `Disallow: /*.pdf$` is the whole file. That is the repository telling
    automated clients not to retrieve documents, and it is the reason this
    build carries no Seminole official statement. Recorded as a row rather
    than a silence, and queued for a user-mediated pull.
    """
    p = os.path.join(RAW, "emma_robots.txt")
    quote = ""
    if os.path.exists(p):
        quote = open(p, encoding="utf-16", errors="replace").read()
        if "Disallow" not in quote:
            quote = open(p, encoding="utf-8", errors="replace").read()
        quote = re.sub(r"[\x00﻿]", "", quote)
        quote = re.sub(r"\s+", " ", quote).strip()
    res = tr.resolve("Seminole Tribe of Florida")
    return dict(
        tribe_id=res["tribe_id"], tribe_canonical_name=res["tribe_canonical_name"],
        obligor_name_as_published="Seminole Tribe of Florida",
        conduit_issuer_as_published="",
        disclosure_class="municipal_continuing_disclosure_repository",
        security_description="", series="", coupon_pct="", maturity_date="",
        amount_usd="", amount_concept="",
        filer_name="Municipal Securities Rulemaking Board",
        filing_form="EMMA official statements and continuing disclosures",
        availability_status="not_retrievable_by_automated_client",
        availability_basis="emma.msrb.org/robots.txt disallows retrieval of "
                           "PDF documents; no document request was made",
        carries_gaming_revenue="unknown_document_not_retrieved",
        revenue_evidence_class="NO_REVENUE_OBSERVATION", measurement_type="",
        entity_match_method=res["match_method"], entity_tier=res["entity_tier"],
        source_authority="Municipal Securities Rulemaking Board, EMMA",
        source_document_type="robots_exclusion_file",
        source_url="https://emma.msrb.org/robots.txt", source_page="",
        source_quote=quote[:400], fetched_date=TODAY)


# --- litigation --------------------------------------------------------------
DOLLAR = re.compile(r"[^.]{0,200}\$\s?[\d][^.]{0,200}\.")
BIGNUM = re.compile(r"[^.]{0,200}\b(billion|million)\b[^.]{0,200}\.", re.I)


def parse_litigation():
    """Scan the West Flagler record for figures actually put on the record."""
    rows, log = [], []
    for m in _manifest_rows("uscourts_opinion", "scotus_filing"):
        p = os.path.join(RAW, m["local_file"])
        if not p.lower().endswith(".pdf"):
            continue
        try:
            doc = fitz.open(p)
        except Exception as e:
            log.append(dict(file=m["local_file"], zone="litigation",
                            status="unreadable", detail=str(e)[:120]))
            continue
        hits = 0
        for pno in range(doc.page_count):
            t = re.sub(r"\s+", " ", doc[pno].get_text())
            for pat, kind in ((DOLLAR, "dollar_figure"),
                              (BIGNUM, "magnitude_word")):
                for mm in pat.finditer(t):
                    q = mm.group(0).strip()
                    if kind == "magnitude_word" and "$" in q:
                        continue
                    rows.append(dict(
                        document=m["doc_label"], doc_class=m["doc_class"],
                        figure_kind=kind, source_page=pno + 1,
                        source_quote=q[:400], source_url=m["source_url"],
                        local_file=m["local_file"]))
                    hits += 1
        log.append(dict(file=m["local_file"], zone="litigation",
                        status="scanned",
                        detail="pages=%d figures=%d" % (doc.page_count, hits)))
        doc.close()
    return rows, log


# --- the negative per-property statement -------------------------------------
FGCC_SCOPE_QUOTE = (
    "Statistical Section - Details various cardroom, pari-mutuel, and slot "
    "statistical data by individual racing association or fronton.")


def no_property_revenue_rows(tr):
    """One explicit NO_REVENUE_OBSERVATION per Florida tribal property.

    Absence from the regulator's per-facility series is a property of that
    series, not of the casino. Florida's per-facility revenue tables are
    permitholder tables; a tribal casino holds no pari-mutuel permit, so it
    can never appear. Saying so on every property is the contract - the
    alternative is a blank that reads as an unworked gap.
    """
    facs = [r for r in _read(FACILITIES) if r.get("state") == "FL"]
    src = next((m for m in _manifest_rows("fgcc_annual_report")), None)
    out = []
    for f in facs:
        res = dict(tribe_id=f.get("tribe_id", ""),
                   tribe_canonical_name=f.get("tribe_canonical_name", ""),
                   match_method="carried_from_gaming_facilities",
                   entity_tier=f.get("entity_tier", ""))
        out.append(dict(
            fund="", direction="", recipient_type="facility",
            tribe_id=res["tribe_id"],
            tribe_canonical_name=res["tribe_canonical_name"],
            party_name_as_published=f.get("tribe", ""),
            facility_id=f["facility_id"], facility_name=f["facility_name"],
            metric="property_revenue_published_by_state_regulator",
            value="", unit="", value_as_published="", published_unit="",
            period_start="", period_end="",
            period_basis="standing_statement_about_the_source",
            period_label="", conference_date="",
            measurement_type="", is_forecast="no",
            revenue_evidence_class="NO_REVENUE_OBSERVATION",
            entity_match_method=res["match_method"],
            entity_tier=res["entity_tier"],
            bound_basis="",
            exclusion_flag="no_such_series_exists",
            exclusion_reason=(
                "Florida publishes per-facility slot revenue, cardroom gross "
                "receipts and pari-mutuel handle for LICENSED PERMITHOLDERS. A "
                "tribal casino operates under the Tribal-State Compact and "
                "holds no pari-mutuel permit, so it is outside the population "
                "of every per-facility series the State publishes. The 2021 "
                "Compact additionally lets the Tribe mark what it does give "
                "the State 'Trade Secret, Confidential and Proprietary'."),
            source_authority=(src or {}).get(
                "source_authority", "Florida Gaming Control Commission"),
            source_document_type="fgcc_annual_report",
            source_url=(src or {}).get(
                "source_url", "https://flgaming.gov/pmw/annual-reports/"),
            source_page="2", source_quote=FGCC_SCOPE_QUOTE,
            source_link_text=(src or {}).get("doc_label", ""),
            zone_header="Report scope", foot_status="", foot_detail="",
            document_status="", fetched_date=(src or {}).get("fetched_date",
                                                             TODAY)))
    return out


def stage_build():
    zonelog = []
    print("[parse] EDR conference documents")
    edr, l1 = parse_edr()
    zonelog += l1
    print("  edr rows: %d" % len(edr))

    print("[parse] compact schedule verification")
    schedules = verify_compact_quotes(zonelog)
    print("  verified schedules: %d" % len(schedules))

    print("[parse] litigation record")
    lit, l2 = parse_litigation()
    zonelog += l2
    print("  litigation figures: %d" % len(lit))

    tr = TribeResolver()
    review = []

    # ----------------------------------------------------------------- pay
    out = []
    seminole = tr.resolve("Seminole Tribe of Florida")
    if not seminole["tribe_id"]:
        raise SystemExit("Seminole Tribe of Florida did not resolve: %s"
                         % seminole["refusal"])
    n_sup = apply_supersession(edr)

    # A forecast moves; a settled actual does not. For every Net Win period,
    # count how many conferences restated it AFTER the period closed and how
    # many distinct values they gave. One value across several post-close
    # conferences is the strongest evidence available here that the figure is
    # a reported actual rather than a estimate that happens to sit in the past.
    stab = defaultdict(list)
    for r in edr:
        if r["metric"].startswith("net_win") and \
                (r.get("conference_date") or "") > r["period_end"]:
            stab[(r["metric"], r["period_end"])].append(r["value"])
    for r in edr:
        k = (r["metric"], r["period_end"])
        if k in stab:
            r["foot_detail"] = ((r.get("foot_detail") or "") +
                                "; post-close statements=%d distinct values=%d"
                                % (len(stab[k]), len(set(stab[k]))))[:300]

    for i, r in enumerate(edr):
        row = {k: "" for k in PAY_FIELDS}
        row.update({k: v for k, v in r.items() if k in PAY_FIELDS})
        row.update(
            payment_id="FLGP-%06d" % (i + 1), state="FL",
            fund="Florida Indian Gaming revenue share",
            direction="paid_in", recipient_type="state_of_florida",
            tribe_id=seminole["tribe_id"],
            tribe_canonical_name=seminole["tribe_canonical_name"],
            party_name_as_published="Seminole Tribe of Florida",
            entity_match_method=seminole["match_method"],
            entity_tier=seminole["entity_tier"],
            unit=("percent" if r["published_unit"] == "percent" else "USD"),
            confidence_tier=Tier.B.value,
            built_date=TODAY, built_by_script=SCRIPT)
        # The Florida payer is the compact tribe. EDR never names a facility
        # and the base is statewide, so facility_id stays empty by rule.
        c = governing(schedules, r["period_end"])
        if c:
            row.update(governing_compact_id=c["compact_id"],
                       compact_rate_schedule=c["schedule"],
                       compact_rate_min_pct=c["rate_min"],
                       compact_rate_max_pct=c["rate_max"],
                       compact_revenue_concept=c["revenue_concept"],
                       compact_base_scope=c["base_scope"],
                       compact_guaranteed_minimum=c["guaranteed_minimum"],
                       compact_term_source_url=c["url"],
                       compact_term_source_quote=c["quote"][:400])
        elif PRE2010["effective_from"] <= r["period_end"] <= PRE2010["effective_to"]:
            row.update(governing_compact_id=PRE2010["compact_id"],
                       compact_rate_schedule="stated guaranteed dollar "
                                             "payments, no percentage of any "
                                             "revenue base")

        # ---------------------------------------------------------------
        # NO DERIVATION IS EMITTED FROM A FLORIDA PAYMENT, AND HERE IS THE
        # ARITHMETIC THAT KILLED THE ONE THAT LOOKED SAFEST.
        #
        # The first pass published `Net Win <= receipts / rate_min` on the
        # ground that every dollar of Net Win is charged at no less than the
        # bottom marginal rate. That inequality is true of the OBLIGATION and
        # false of the RECEIPTS, and EDR publishes receipts:
        #
        #   FY 2013/14 receipts        $237,312,301   ->  bound "Net Win <= $1.978bn"
        #   EDR's own Net Win, same FY               $2.098bn      -> BOUND VIOLATED
        #
        # The gap is the true-up. EDR states the mechanism in the document:
        #   "Revenues collected are lagged by one month"
        #   "True-up payments generated from activity in any Fiscal Year are
        #    received in the following Fiscal Year."
        # so a state fiscal year's cash is one cycle's instalments plus the
        # PREVIOUS cycle's true-up. Period does not match on both sides, and
        # the rule is to refuse rather than caveat.
        #
        # Two further blockers survive even with a matched period: the payment
        # is max(percentage amount, guaranteed minimum) and a binding minimum
        # carries no information about Net Win at all; and under the 2021
        # Compact the total is a sum over four category schedules, so one total
        # does not determine the four bases.
        # ---------------------------------------------------------------
        NO_DERIV = (
            "Refused, not caveated. The published figure is CASH RECEIVED in a "
            "state fiscal year and the compact's rate applies to a Revenue "
            "Sharing Cycle's Net Win. EDR states the mismatch itself - "
            "'Revenues collected are lagged by one month' and 'True-up "
            "payments generated from activity in any Fiscal Year are received "
            "in the following Fiscal Year' - and the arithmetic confirms it: "
            "FY 2013/14 receipts of $237,312,301 give an apparent ceiling of "
            "$1.978bn on Net Win, while EDR's own Net Win for that year is "
            "$2.098bn. Two further blockers survive a matched period: the "
            "payment is max(percentage amount, guaranteed minimum) and a "
            "binding minimum carries no information about Net Win; and under "
            "the 2021 Compact one total is the sum of four category schedules "
            "and does not determine the four bases.")

        if r["metric"].startswith("net_win") and r["is_forecast"] == "no":
            # Not a derivation. EDR states this figure as the actual Net Win
            # for a closed year, sourced from the Tribe's own quarterly
            # financial reports. Tribe-level; the base is every Facility plus,
            # from 2021, a statewide mobile product.
            row["revenue_evidence_class"] = "TRIBE_LEVEL_REVENUE"
            row["compact_revenue_concept"] = "Net Win"
            row["compact_base_scope"] = "tribe"
            row["payment_invertible"] = "not_applicable_this_row_is_a_revenue_figure"
            row["bound_basis"] = (
                "Stated by the State, not derived here. EDR's December 2015 "
                "conference names its source: 'the actual Net Win for Fiscal "
                "Year 2014-15, and other information from the most recent "
                "quarterly financial reports available from the Tribe'. The "
                "figure is Net Win as the compact defines it, for the whole "
                "tribe. It is not a property figure and cannot be split to one.")
        elif r["metric"] == "revenue_share_obligation_for_cycle" and \
                r["is_forecast"] == "no":
            row["revenue_evidence_class"] = "NO_REVENUE_OBSERVATION"
            row["payment_invertible"] = "obligation_for_the_cycle_not_cash_received"
            row["bound_basis"] = (
                "The amount owed for the cycle under the schedule, which is "
                "not the amount received in any one state fiscal year.")
        elif r["is_forecast"] == "yes":
            row["revenue_evidence_class"] = "NO_REVENUE_OBSERVATION"
            row["payment_invertible"] = "not_a_payment_a_state_forecast"
            row["bound_basis"] = (
                "A Revenue Estimating Conference forecast. EDR estimates Net "
                "Win in order to forecast the payment; for a period that had "
                "not closed there is no reported figure behind it.")
        elif r["published_unit"] == "percent":
            row["revenue_evidence_class"] = "NO_REVENUE_OBSERVATION"
            row["payment_invertible"] = "a_rate_not_an_amount"
            row["bound_basis"] = NO_DERIV
        elif r["metric"] in ("receipts_total_received",
                             "monthly_collections_total"):
            row["revenue_evidence_class"] = "NO_REVENUE_OBSERVATION"
            row["payment_invertible"] = "no_period_mismatch_and_guaranteed_minimum"
            row["bound_basis"] = NO_DERIV
        else:
            row["revenue_evidence_class"] = "NO_REVENUE_OBSERVATION"
            row["payment_invertible"] = "component_of_a_payment_not_the_payment"
            row["bound_basis"] = (
                "A destination split of a payment recorded in full elsewhere "
                "in this file; deriving on it would double count. " + NO_DERIV)
        out.append(row)

    for i, nr in enumerate(no_property_revenue_rows(tr)):
        row = {k: "" for k in PAY_FIELDS}
        row.update({k: v for k, v in nr.items() if k in PAY_FIELDS})
        row.update(payment_id="FLGP-N%05d" % (i + 1), state="FL",
                   confidence_tier=Tier.B.value, built_date=TODAY,
                   built_by_script=SCRIPT)
        out.append(row)

    # ---------------------------------------------------------------- bonds
    bonds = []
    bonds += parse_sec_holdings(tr, review)
    bonds += parse_fac(tr)
    bonds.append(emma_row(tr))
    # the seed: what Cedar already held, carried with its own provenance so the
    # new rows are readable against it rather than instead of it
    seed = os.path.join(CLEAN, "tribal_bond_issuances.csv")
    if os.path.exists(seed):
        for r in _read(seed):
            if "Seminole Tribe of Florida" not in r.get("issuer", ""):
                continue
            res = tr.resolve(r["issuer"])
            bonds.append(dict(
                tribe_id=res["tribe_id"],
                tribe_canonical_name=res["tribe_canonical_name"],
                obligor_name_as_published=r["issuer"],
                conduit_issuer_as_published="",
                disclosure_class="rating_agency_action",
                security_description=r.get("instrument_type", ""),
                series="", coupon_pct="",
                maturity_date=r.get("maturity", ""),
                amount_usd=r.get("par_amount", ""),
                amount_concept="par amount as quoted in the rating action",
                rating=r.get("rating_at_issue", ""),
                rating_agency=r.get("rating_agency", ""),
                filer_name=r.get("rating_agency", ""), filer_cik="",
                filing_form="rating action", filing_date="",
                fiscal_year="", period_end="",
                availability_status="carried_from_tribal_bond_issuances",
                availability_basis="Row already held by Cedar; re-checked "
                                   "here for tribe and state agreement only.",
                carries_gaming_revenue="no",
                revenue_evidence_class="NO_REVENUE_OBSERVATION",
                measurement_type="",
                entity_match_method=res["match_method"],
                entity_tier=res["entity_tier"],
                source_authority=r.get("rating_agency", ""),
                source_document_type="rating_agency_press_release",
                source_url=r.get("source_url", ""), source_page="",
                source_quote=(r.get("notes") or r.get("date_basis") or "")[:400],
                fetched_date=r.get("retrieved_date", "")))
    for i, b in enumerate(bonds):
        b.setdefault("confidence_tier", Tier.B.value)
        b["disclosure_id"] = "SMBD-%04d" % (i + 1)
        b["built_date"] = TODAY
        b["built_by_script"] = SCRIPT
        for k in BOND_FIELDS:
            b.setdefault(k, "")

    # --------------------------------------------------------------- review
    # Everything a human has to rule on, in the standing queue shape.
    review.append(dict(
        review_id="FL-EMMA-SEMINOLE-OS",
        issue_type="agent_user_mediated_pull_required",
        name_as_published="Seminole Tribe of Florida / Capital Trust Agency, FL",
        context="MSRB EMMA official statements and continuing disclosures",
        evidence="emma.msrb.org/robots.txt is exactly 'User-agent: * / "
                 "Disallow: /*.pdf$'. The disclosure documents are PDFs, so an "
                 "automated client may not retrieve them. Two conduit issues "
                 "are now identified from SEC fund holdings and give EMMA "
                 "search terms: Capital Trust Agency, FL Revenue Bonds Series "
                 "2001 10.00% and Series 2003A 8.95%, both 'Seminole Tribe of "
                 "Florida Convention and Resort Hotel Facilities', 10/1/2033.",
        question="Download the Seminole Tribe of Florida / Capital Trust "
                 "Agency official statements and continuing disclosure "
                 "filings from EMMA by hand and drop them in "
                 "data/raw/external/fl_gaming/. Which ones exist?",
        candidate_entities="TRBF-SMNLFL-00",
        source_url="https://emma.msrb.org/robots.txt",
        source_quote="User-agent: * Disallow: /*.pdf$", YOUR_RULING=""))
    review.append(dict(
        review_id="FL-COMPACT-RATE-10PCT-INVERTIBILITY",
        issue_type="agent_conflict_with_existing_dataset",
        name_as_published="CMP-FL-seminole-tribe-of-florida-20210811",
        context="compact_structured_terms.csv, term_field=revenue_sharing_rate",
        evidence="The compact parse records a Florida revenue_sharing_rate of "
                 "10 with formula_invertibility=INVERTIBLE_FLAT_RATE and "
                 "revenue_evidence_class=TRIBE_LEVEL_REVENUE. Read in place, "
                 "Part XI.C.1(k) makes 10% the bottom tier of a graduated "
                 "schedule for ONE game category, under a compact that also "
                 "carries a $2.5bn guaranteed minimum. This build does not use "
                 "it and derives an upper bound instead.",
        question="Demote the Florida INVERTIBLE_FLAT_RATE row to "
                 "NOT_INVERTIBLE in compact_structured_terms.csv? That file is "
                 "owned by 95_parse_compact_terms.py and was not edited here.",
        candidate_entities="TRBF-SMNLFL-00",
        source_url="https://www.bia.gov/sites/default/files/dup/assets/as-ia/"
                   "oig/pdf/508%20Compliant%202021.08.11%20Seminole%20Tribe%20"
                   "Gaming%20Compact.pdf",
        source_quote="(k) Ten percent (10%) of Net Win received by the Tribe "
                     "from the operation and play of Sports Betting, during "
                     "each Revenue Sharing Cycle, on such wagering by Patrons "
                     "who access the Tribe's wagering platform via software "
                     "that uses a brand of a Qualified Pari-mutuel "
                     "Permitholder", YOUR_RULING=""))
    for b in bonds:
        if b["disclosure_class"] == "single_audit_reporting_package" and \
                b["availability_status"] == "withheld_by_rule":
            review.append(dict(
                review_id="FL-FAC-OPTIN-%s" % b["fiscal_year"],
                issue_type="agent_access_route_needs_a_decision",
                name_as_published=b["obligor_name_as_published"],
                context="Federal Audit Clearinghouse, FY%s" % b["fiscal_year"],
                evidence=b["source_quote"],
                question="The Tribe's audited reporting package is filed and "
                         "withheld under 2 CFR 200.512(b)(2). Request it "
                         "directly from the Tribe, or leave the year recorded "
                         "as structurally unavailable?",
                candidate_entities=b["tribe_id"],
                source_url=b["source_url"],
                source_quote=b["availability_basis"][:400], YOUR_RULING=""))

    # ------------------------------------------------------------- integrity
    bad = [r for r in out if not r["source_url"] or not r["source_quote"]]
    assert not bad, "%d payment rows without source_url or source_quote" % len(bad)
    badb = [b for b in bonds if not b["source_url"] or not b["source_quote"]]
    assert not badb, "%d bond rows without provenance" % len(badb)
    badp = [r for r in out
            if r["revenue_evidence_class"] in ("REPORTED_PROPERTY_REVENUE",
                                               "EXACT_DERIVED_PROPERTY_REVENUE")]
    assert not badp, "%d Florida rows claim property revenue" % len(badp)
    badf = [r for r in out if r["derived_revenue_bound_value"] != ""
            and r["derived_revenue_scope"] != "tribe"]
    assert not badf, "%d derived bounds are not tribe-scoped" % len(badf)
    badt = [r for r in out + bonds
            if r["tribe_id"] and r["tribe_id"] not in ("TRBF-SMNLFL-00",
                                                       "TRBF-MCSKEE-00")]
    assert not badt, ("%d rows resolved outside the Florida tribes: %s"
                      % (len(badt), {r["tribe_id"] for r in badt}))

    # ---------------------------------------------------------------- write
    p1 = os.path.join(CLEAN, "fl_gaming_payments.csv")
    with open(p1, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PAY_FIELDS)
        w.writeheader()
        w.writerows(out)
    p2 = os.path.join(CLEAN, "seminole_bond_disclosures.csv")
    with open(p2, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=BOND_FIELDS)
        w.writeheader()
        w.writerows(bonds)
    ded, seen = [], set()
    for r in review:
        if r["review_id"] in seen:
            continue
        seen.add(r["review_id"])
        ded.append(r)
    p3 = os.path.join(REVIEW, "fl_gaming_unresolved_%s.csv" % TODAY)
    with open(p3, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
        w.writeheader()
        w.writerows(ded)
    with open(os.path.join(INTERIM, "105_zone_log.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "zone", "status", "detail"])
        w.writeheader()
        w.writerows(zonelog)
    with open(os.path.join(INTERIM, "105_litigation_figures.csv"), "w",
              encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["document", "doc_class",
                                          "figure_kind", "source_page",
                                          "source_quote", "source_url",
                                          "local_file"])
        w.writeheader()
        w.writerows(lit)

    # ---------------------------------------------------------- run summary
    L = []
    A = L.append
    A("Cedar Press 105 - Florida / Seminole gaming        %s" % TODAY)
    A("=" * 74)
    docs = _manifest_rows()
    A("documents on disk            %d" % len(docs))
    for k, v in Counter(d["doc_class"] for d in docs).most_common():
        A("   %-38s %4d" % (k, v))
    A("")
    A("payment rows                 %d" % len(out))
    A("bond/disclosure rows         %d" % len(bonds))
    A("review rows                  %d" % len(ded))
    A("restated by later conference %d" % n_sup)
    A("")
    A("BY METRIC")
    for k, v in Counter(r["metric"] for r in out).most_common():
        per = [r["period_end"] for r in out if r["metric"] == k and r["period_end"]]
        A("  %-52s %5d  %s .. %s"
          % (k, v, min(per) if per else "", max(per) if per else ""))
    A("")
    A("REVENUE EVIDENCE CLASS")
    for k, v in Counter(r["revenue_evidence_class"] for r in out).most_common():
        A("  %-52s %5d" % (k, v))
    A("  derived upper bounds on Net Win                    %5d"
      % sum(1 for r in out if r["derived_revenue_bound_value"] != ""))
    A("  rows claiming property revenue                     %5d" % 0)
    A("")
    A("EXCLUSIONS (columns, never deletions)")
    for k, v in Counter(r["exclusion_flag"] for r in out).most_common():
        A("  %-52s %5d" % (k or "(none)", v))
    A("")
    A("FOOTING (the document's own printed totals)")
    for k, v in Counter(z["status"] for z in zonelog).most_common():
        A("  %-52s %5d" % (k, v))
    A("")
    A("BOND / AUDITED DISCLOSURE")
    for k, v in Counter(b["disclosure_class"] for b in bonds).most_common():
        A("  %-52s %5d" % (k, v))
    for k, v in Counter(b["availability_status"] for b in bonds).most_common():
        A("  availability: %-38s %5d" % (k, v))
    A("")
    A("LITIGATION RECORD")
    A("  documents scanned                                  %5d"
      % len(_manifest_rows("uscourts_opinion", "scotus_filing")))
    A("  dollar figures on the record                       %5d"
      % sum(1 for r in lit if r["figure_kind"] == "dollar_figure"))
    A("  magnitude words without a figure                   %5d"
      % sum(1 for r in lit if r["figure_kind"] == "magnitude_word"))
    A("")
    A("ENTITY RESOLUTION")
    for k, v in tr.reasons.most_common():
        A("  %-52s %5d" % (k, v))
    txt = "\n".join(L)
    with open(os.path.join(INTERIM, "105_run_summary.txt"), "w",
              encoding="utf-8") as f:
        f.write(txt + "\n")
    print()
    print(txt)
    return out, bonds, ded


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    if a.stage in ("all", "discover"):
        print("[discover]")
        stage_discover()
    if a.stage in ("all", "fetch"):
        print("[fetch]")
        stage_fetch(a.limit)
        stage_fetch_sec_documents()
    if a.stage in ("all", "parse", "build", "emit"):
        stage_build()
