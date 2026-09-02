#!/usr/bin/env python3
"""
103 - California gaming: the CGCC / CA-DOJ regulator layer.

WHY THIS SCRIPT EXISTS
----------------------
`code/95_parse_compact_terms.py` mapped 4,121 reporting obligations across 27
states and found that **California carries 171 compacts with a reporting
obligation while Cedar held no California regulator file at all** - the largest
unworked seam in the gaming dataset, in the largest tribal gaming market in the
country (NIGC Sacramento region, $12.631B, FY2025).

The compacts prove California *holds* the series. This script goes and gets the
part California *publishes*.

WHAT CALIFORNIA PUBLISHES, AND WHAT IT DOES NOT
-----------------------------------------------
The California Gambling Control Commission publishes the Indian Gaming Revenue
Sharing Trust Fund (RSTF) quarterly distribution reports, ~100 of them, 2001 to
current. Each carries two tribe-identified money tables:

  Exhibit 1  - the distribution TO each eligible recipient tribe (the
               non-gaming and limited-gaming tribes), per quarter.
  Exhibit 3  - the revenue received FROM each compact tribe, fiscal year to
               date and inception to date.

Both are **payments**, not revenue. See the invertibility note below.

THE TWO RULES THIS BUILD IS BUILT AROUND
----------------------------------------
1. **A payment is not revenue.** An RSTF or SDF payment is a compact-mandated
   transfer. It becomes a revenue statement only where the compact makes it an
   invertible flat rate against a stated base, and then only at the scope of
   that base. Script 95 already measured California's base: *"its Net Win from
   the operation of Gaming Devices"* is **tribe-level, not per-facility** (44
   rows were demoted for exactly this). So no California derivation can reach
   `EXACT_DERIVED_PROPERTY_REVENUE`; the ceiling is `TRIBE_LEVEL_REVENUE`.
   Every candidate has its base clause checked against
   `compact_structured_terms.csv` rather than assumed.

2. **A device licence is an entitlement, not a floor.** California's Gaming
   Device licences are drawn from a statewide pool. A licence count is
   `AUTHORIZED_MAXIMUM` and `cedar_domain.may_promote()` refuses to turn it
   into `ACTIVE_FLOOR_COUNT`. Asserted at import.

Stages:  discover | fetch | parse | resolve | emit   (default: all)

Writes:
  data/raw/external/ca_gaming/                     raw PDFs + _SOURCE_MANIFEST.csv
  data/clean/ca_gaming_payments.csv
  data/clean/ca_gaming_facilities_official.csv
  review/ca_gaming_unresolved_<date>.csv
  data/interim/103_run_summary.txt

Does NOT write: gaming_facilities.csv, gaming_capacity_official.csv,
compact_*.csv, nigc_*, the spine, the identifier ledger, entity_aliases.csv,
entity_relationships.csv.
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
RAW = os.path.join(ROOT, "data", "raw", "external", "ca_gaming")
CLEAN = os.path.join(ROOT, "data", "clean")
INTERIM = os.path.join(ROOT, "data", "interim")
REVIEW = os.path.join(ROOT, "review")
LOGS = os.path.join(ROOT, "logs")
for d in (RAW, CLEAN, INTERIM, REVIEW, LOGS):
    os.makedirs(d, exist_ok=True)

TODAY = dt.date.today().isoformat()
HOST = "cgcc.ca.gov"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
GAP = 1.6          # seconds between requests to a single host

# ---------------------------------------------------------------------------
# Shared vocabulary and the ONE resolver. Never re-implement either.
# ---------------------------------------------------------------------------
sys.path.insert(0, CODE)
from cedar_domain import (                       # noqa: E402
    MeasurementType, may_promote, REVENUE_EVIDENCE, NAME_TRAPS, Tier,
    INSTITUTION_CLASSES, ENTITY_CLASSES, entity_class_is_declared,
)

_spec = importlib.util.spec_from_file_location(
    "party_rulings", os.path.join(CODE, "33_apply_party_rulings.py"))
_pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pr)
resolve_entity = _pr.resolve_entity

# Enforced in code, not in prose: a California device licence is an entitlement
# drawn from a statewide pool and may never become an operating count.
assert not may_promote(MeasurementType.AUTHORIZED_MAXIMUM,
                       MeasurementType.ACTIVE_FLOOR_COUNT)
assert not may_promote(MeasurementType.PROJECTED,
                       MeasurementType.ACTIVE_FLOOR_COUNT)
assert "EXACT_DERIVED_PROPERTY_REVENUE" in REVENUE_EVIDENCE
assert "TRIBE_LEVEL_REVENUE" in REVENUE_EVIDENCE

# Entity classes a gaming regulator's payment file can never be about. This is
# the Chickasaw Children's Village refusal (AGENTS.md) applied here: a refusal,
# not a second matcher.
#
# CORRECTED 2026-08-26 by `code/442_consolidate_entity_class_vocabulary.py`.
# THIS GUARD WAS TWO-FIFTHS DEAD FOR AS LONG AS IT HAS EXISTED. It refused the
# literals `Native CDFI` and `Native financial institution` - and NEITHER
# STRING IS IN THE SPINE. The spine says
# `Native Community Development Financial Institution` (64 rows) and
# `Native Financial Institution` (29), so **93 entities passed a refusal that
# had never once matched**, on a table that keys gaming payments.
# `107_pull_remaining_states.py` and `92_build_gaming_capacity_official.py`
# spell the same five classes correctly, which is how we know the rename
# happened and this file was not brought along.
#
# It is now IMPORTED, not retyped. `INSTITUTION_CLASSES` is the same five
# classes, declared once in `cedar_domain`, and a class name that only exists
# in a string literal is exactly how the last one died.
REFUSED_ENTITY_CLASSES = INSTITUTION_CLASSES

# A guard whose members are not in the spine filters nothing, and it does so
# silently. Asserted at MODULE LOAD so the failure is at import rather than in
# a refusal counter nobody reads.
assert REFUSED_ENTITY_CLASSES <= ENTITY_CLASSES, (
    "REFUSED_ENTITY_CLASSES carries a string the spine does not: "
    + repr(sorted(REFUSED_ENTITY_CLASSES - ENTITY_CLASSES)))
assert all(entity_class_is_declared(c) for c in REFUSED_ENTITY_CLASSES)


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def claim_host(host, queue):
    """PULL_DISCIPLINE rule 2. One poller per host; append and exit otherwise."""
    p = os.path.join(LOGS, f"_HOSTLOCK_{host}.json")
    if os.path.exists(p):
        try:
            cur = json.load(open(p))
        except Exception:
            cur = {}
        if cur.get("script") not in (None, "", os.path.relpath(__file__, ROOT),
                                     "code/103_build_california_gaming.py"):
            cur.setdefault("queue", []).extend(queue)
            json.dump(cur, open(p, "w"), indent=1)
            print(f"  host {host} already claimed by {cur.get('script')}; "
                  f"queued and deferring")
            return False
    json.dump({"host": host, "pid": os.getpid(),
               "script": "code/103_build_california_gaming.py",
               "started": dt.datetime.now(dt.timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%SZ"),
               "queue": queue}, open(p, "w"), indent=1)
    return True


_last_hit = defaultdict(float)


def curl(url, dest=None, timeout=120):
    """Single-stream GET with a declared UA. Returns (status, content_type, bytes).

    CGCC hrefs contain literal spaces (`RSTF Distrib 47th_CommStaffReport
    FINAL.pdf`). curl refuses those with status 0 - which reads like a network
    failure and is not one. 13 reports were lost to it on the first pass.
    """
    url = url.replace(" ", "%20")
    host = re.sub(r"^https?://([^/]+).*$", r"\1", url)
    wait = GAP - (time.time() - _last_hit[host])
    if wait > 0:
        time.sleep(wait)
    cmd = ["curl", "-s", "-L", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
           "--max-time", str(timeout),
           "-w", "\n__META__%{http_code}|%{content_type}", url]
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
# STAGE 1 - discover
# ===========================================================================
CGCC_PAGES = [
    ("tribalinfo", "https://cgcc.ca.gov/?pageID=tribalinfo"),
    ("rstfi", "https://cgcc.ca.gov/?pageID=rstfi"),
    ("sdf", "https://cgcc.ca.gov/?pageID=sdf"),
    ("leg_report", "https://cgcc.ca.gov/?pageID=leg_report"),
    ("reports_2", "https://cgcc.ca.gov/?pageID=reports_2"),
    ("compacts", "https://cgcc.ca.gov/?pageID=compacts"),
    ("SecretarialProcedures", "https://cgcc.ca.gov/?pageID=SecretarialProcedures"),
    ("tribal_gaming_regulations",
     "https://cgcc.ca.gov/?pageID=tribal_gaming_regulations"),
    ("gaming", "https://cgcc.ca.gov/?pageID=gaming"),
    ("home", "https://cgcc.ca.gov/"),
]
# California DOJ, Bureau of Gambling Control.
DOJ_PAGES = [
    ("doj_gambling", "https://oag.ca.gov/gambling"),
    ("doj_tribal", "https://oag.ca.gov/gambling/tribal"),
    ("doj_publications", "https://oag.ca.gov/gambling/publications"),
]

DISCOVERED = os.path.join(RAW, "_discovered_links.csv")


def _anchors(page_html, base):
    out = []
    for m in re.finditer(r"<a[^>]+href=\"([^\"]+)\"[^>]*>(.*?)</a>",
                         page_html, re.S | re.I):
        href = html.unescape(m.group(1)).strip()
        text = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        text = re.sub(r"\s+", " ", text).strip()
        if href.startswith("#") or href.lower().startswith("mailto:"):
            continue
        href = href.replace("../../", "/")
        if href.startswith("/"):
            href = base + href
        elif not href.startswith("http"):
            href = base + "/" + href
        out.append((href, text))
    return out


def stage_discover():
    if not claim_host(HOST, ["cgcc rstf/sdf/tribal document sweep"]):
        return
    claim_host("oag.ca.gov", ["ca doj bureau of gambling control sweep"])
    rows = []
    for name, url in CGCC_PAGES + DOJ_PAGES:
        base = "https://" + re.sub(r"^https?://([^/]+).*$", r"\1", url)
        dest = os.path.join(RAW, f"page_{name}.html")
        st, ct, body = curl(url, dest)
        print(f"  page {name:26s} {st} {len(body):>7d}")
        if st != 200:
            continue
        h = body.decode("utf-8", "replace")
        for href, text in _anchors(h, base):
            rows.append(dict(page=name, url=href, link_text=text))
    with open(DISCOVERED, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page", "url", "link_text"])
        w.writeheader()
        w.writerows(rows)
    docs = [r for r in rows if r["url"].lower().split("?")[0].endswith(
        (".pdf", ".xlsx", ".xls", ".csv", ".doc", ".docx"))]
    print(f"  discovered {len(rows)} links, {len(docs)} documents, "
          f"{len({d['url'] for d in docs})} distinct")


# ===========================================================================
# STAGE 2 - fetch
# ===========================================================================
# Which discovered documents are in scope. Precision over recall: a filename
# that only *looks* like tribal gaming (CGCC's GGR24_080425.pdf is a re-hosted
# NIGC national report) is confirmed by content in the parse stage, not here.
KEEP_PAT = re.compile(
    r"/documents/(rstfi|sdf|tribal|publications)/|"
    r"RSTF|SDF|TNGF|Casino|Tribal|Special_Distribution|Federally_Recognized|"
    r"Indian_Gaming|Indian%20Gaming|"
    # TNGF grant-program website reports are named for the grant type
    # (ERG / EQD / CBG / Capacity / ImpactGrant), not for the fund.
    r"/(FY_?\d\d-\d\d_)?(ERG|EQD|CBG)(_|\.)|Capacity_Website_Report|ImpactGrant|"
    # 2008 tribal MOAs / LOAs sit under /documents/enabling/.
    r"/(MOA|LOA)%20", re.I)
SKIP_PAT = re.compile(
    # /documents/compacts/ is the compact corpus. `compacts.csv` and
    # `compact_structured_terms.csv` are owned by another build and this script
    # must not create a second compact universe. The CGCC compacts PAGE is kept
    # (it is a dated tribe -> governing-instrument roster and that is what makes
    # the invertibility join possible) but the 316 PDFs behind it are not
    # re-downloaded here.
    r"/documents/compacts/|"
    r"Rulemaking_Calendar|Newsletter|Precedential|Public_Meetings|"
    r"GPAC|Cybersecurity|Strategic|Badge_Mailing|Moratorium", re.I)


def _local_name(url):
    tail = url.split("/documents/", 1)[-1] if "/documents/" in url else \
        url.rsplit("/", 1)[-1]
    tail = re.sub(r"[?&=%]+", "_", tail)
    tail = re.sub(r"[\\/]+", "__", tail)
    tail = re.sub(r"[^A-Za-z0-9._-]+", "_", tail)
    return tail[:150]


MANIFEST = os.path.join(RAW, "_SOURCE_MANIFEST.csv")
MAN_FIELDS = ["local_file", "source_url", "source_page", "link_text",
              "doc_class", "http_status", "content_type", "bytes", "md5",
              "fetched_date"]


def _doc_class(url, text):
    u = url.lower()
    if "/documents/rstfi/" in u and re.search(r"shortfall", u + " " + text, re.I):
        return "rstf_shortfall_notification"
    if re.search(r"rstf|revenue.sharing|distribfundreport|funddist|report\d{6}",
                 u) and "/documents/rstfi/" in u:
        return "rstf_quarterly_distribution"
    if "tngf" in u:
        return "tngf_report"
    if re.search(r"list_of_casinos|list_of-casinos", u):
        return "cgcc_casino_list"
    if re.search(r"list_of_rstf_eligible", u):
        return "cgcc_rstf_eligible_list"
    if re.search(r"list_of_tribes_currently_making_payments", u):
        return "cgcc_paying_tribes_list"
    if re.search(r"federally_recognized", u):
        return "cgcc_federally_recognized_list"
    if re.search(r"cardrooms_and_casinos_map", u):
        return "cgcc_casino_map"
    if re.search(r"special_distribution|sdf|available_fund_balance", u):
        return "sdf_report"
    return "other"


def stage_fetch(limit=None):
    if not os.path.exists(DISCOVERED):
        stage_discover()
    with open(DISCOVERED, encoding="utf-8") as f:
        links = list(csv.DictReader(f))
    seen, todo = set(), []
    for r in links:
        u = r["url"]
        if not u.lower().split("?")[0].endswith((".pdf", ".xlsx", ".xls", ".csv")):
            continue
        if SKIP_PAT.search(u) or not KEEP_PAT.search(u):
            continue
        if u in seen:
            continue
        seen.add(u)
        todo.append(r)
    print(f"  {len(todo)} documents in scope")

    have = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8-sig") as f:
            have = {r["source_url"]: r for r in csv.DictReader(f)}

    out = dict(have)
    n_new = n_fail = 0
    for i, r in enumerate(todo):
        if limit and n_new >= limit:
            break
        url = r["url"]
        if url in have and have[url].get("http_status") == "200":
            continue
        fn = _local_name(url)
        dest = os.path.join(RAW, fn)
        st, ct, body = curl(url, dest)
        ok = st == 200 and body[:5] in (b"%PDF-", b"PK\x03\x04") or (
            st == 200 and not fn.lower().endswith(".pdf"))
        if st == 200 and fn.lower().endswith(".pdf") and body[:5] != b"%PDF-":
            # CGCC serves an HTML soft-404 with status 200 - the ADG trap.
            ok = False
            if os.path.exists(dest):
                os.remove(dest)
        out[url] = dict(local_file=fn if ok else "", source_url=url,
                        source_page=r["page"], link_text=r["link_text"],
                        doc_class=_doc_class(url, r["link_text"]),
                        http_status=st, content_type=ct, bytes=len(body),
                        md5=md5(dest) if ok and os.path.exists(dest) else "",
                        fetched_date=TODAY)
        if ok:
            n_new += 1
        else:
            n_fail += 1
            print(f"    FAIL {st} {ct[:30]:30s} {url[:110]}")
        if (i + 1) % 20 == 0:
            print(f"    ... {i+1}/{len(todo)} ok={n_new} fail={n_fail}")
            _write_manifest(out)
    _write_manifest(out)
    print(f"  fetched {n_new} new, {n_fail} failed, "
          f"{sum(1 for v in out.values() if v['local_file'])} total on disk")


def _write_manifest(out):
    with open(MANIFEST, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MAN_FIELDS)
        w.writeheader()
        for v in sorted(out.values(), key=lambda x: (x["doc_class"],
                                                     x["source_url"])):
            w.writerow({k: v.get(k, "") for k in MAN_FIELDS})


# ===========================================================================
# STAGE 3 - parse.  A positional reader, because the linear text layer lies.
# ===========================================================================
# `pdftotext -layout` shifts a column by one row whenever a table sets labels
# and values on baselines a point or two apart. Confirmed in this repo for the
# Michigan payment tables, the Michigan annual report, the Arizona Gaming Status
# Report and the Florida EDR forecast. The CGCC reports have the same shape -
# the row index sits ~3pt above the tribe's own baseline. So: read word
# positions, assign every number to a column by its RIGHT edge, and foot the
# result against the document's own printed Totals row. A zone that does not
# foot is not published.
import fitz  # noqa: E402  (PyMuPDF)

MONEY_RE = re.compile(r"^\(?\$?\s*-?\$?\s*(\d{1,3}(,\d{3})+|\d+)(\.\d{1,2})?\)?$")
BARE_INT_RE = re.compile(r"^\d{1,2}$")


ZERO_FRAGMENT_RE = re.compile(r"^\.0{1,2}$")

# A NUMBER SPLIT ACROSS TWO TEXT SPANS. Same family as ZERO_FRAGMENT_RE, and
# the reason `docs/datasets/gaming_sources.md` 1E could say the CA RSTF 93rd
# report "has 37,974 characters of extractable text and yields ZERO rows".
#
# MEASURED 2026-09-01 on that document. Two of its 89 Exhibit-1 rows render
# `25,438,385.42` as the two words `25,438` and `,385.42`, 2.74pt apart. The
# leading half is money-shaped so it lands in a column; the trailing half is
# not, so it fell into the row LABEL ("Pinoleville Pomo Nation ,385.42"). The
# 2.74pt offset then opened a FIFTH column holding exactly two values, and
# `metric_for` has no five-column mapping - so all five columns were reported
# `unmapped_column` and the entire 89-row exhibit produced nothing. The same
# artifact accounts for 890 of the 1,189 rows in `data/interim/103_zone_log.csv`.
#
# The document verifies the repair, which is why it is a repair and not a
# guess: rejoined, the inception-to-date column sums to $1,826,037,694.56
# against a printed total of $1,826,037,694.56, exactly, where before it was
# $50,876,770.84 short - twice the missing $25,438,385.42.
#
# The gap test is what keeps this from gluing two real numbers together. A
# within-number split measures 2.74pt here; the narrowest gap BETWEEN columns
# in these tables is over 30pt.
SPLIT_MONEY_TAIL_RE = re.compile(r"^,\d{3}(\.\d{1,2})?$")
SPLIT_MONEY_HEAD_RE = re.compile(r"^\(?\$?\s*-?\d{1,3}(,\d{3})*$")
SPLIT_MONEY_MAX_GAP_PT = 6.0


def rejoin_split_money(words):
    """Glue `25,438` + `,385.42` back into one word. Returns a new list."""
    out = []
    for w in words:
        if (out and SPLIT_MONEY_TAIL_RE.match(w["text"])
                and SPLIT_MONEY_HEAD_RE.match(out[-1]["text"])
                and 0 <= w["x0"] - out[-1]["x1"] < SPLIT_MONEY_MAX_GAP_PT):
            p = dict(out[-1])
            p["text"] = p["text"] + w["text"]
            p["x1"] = max(p["x1"], w["x1"])
            p["split_rejoined"] = True
            out[-1] = p
            continue
        out.append(w)
    return out
# From the 2016 reports on, CGCC prints `--` with footnote 2 against several
# tribes and reports their combined figure on one `Aggregate Total for Tribes`
# line. That is SUPPRESSION, not absence, and the two must not be conflated: a
# dash cell is published with no value and an explicit reason, never as zero.
DASH_RE = re.compile(r"^[-\u2010-\u2015]{1,3}$")


def _is_dash(s):
    return bool(DASH_RE.match((s or "").strip()))


def _is_money(t):
    """A money token carries a thousands separator or cents, or is a bare 0.

    Requiring that is what keeps a row index (`1`, `47`) and a footnote marker
    out of the number columns without needing to guess from position.

    `.00` IS ACCEPTED AS ZERO. These reports are Excel exports and the content
    stream of an exact-zero cell genuinely contains only `.00` - the leading
    glyph is absent from the text layer, not from the page. Verified char by
    char in the 29th staff report: span `.00` at x=[275.8, 289.7], right edge
    identical to every other cell in that column. Only `.0` and `.00` are
    accepted; any other bare decimal fragment is refused, because there the
    missing leading digits would change the value.
    """
    t = t.strip()
    if t in {"0", "$0", "-", "$-"}:
        return True
    if ZERO_FRAGMENT_RE.match(t):
        return True
    if not MONEY_RE.match(t):
        return False
    return ("," in t) or ("." in t)


def _money_val(t):
    t = t.strip()
    if t in {"-", "$-"} or ZERO_FRAGMENT_RE.match(t):
        return 0.0
    neg = t.startswith("(") and t.endswith(")")
    v = float(re.sub(r"[^\d.]", "", t) or 0)
    return -v if neg else v


def page_words(page):
    """Words with exact bboxes. Superscript footnote markers dropped.

    A footnote marker is a 1-2 digit integer set materially smaller than the
    page's modal body size. That is a targeted refusal, not a size filter over
    everything: dropping all small text would have taken the row indices too,
    and in some editions the body IS 9pt.
    """
    d = page.get_text("rawdict")
    sizes = Counter()
    for b in d["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                if s.get("text", "").strip():
                    sizes[round(s["size"], 1)] += len(s["text"])
    modal = sizes.most_common(1)[0][0] if sizes else 11.0
    words = []
    for b in d["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                cur = None
                for ch in s.get("chars", []):
                    c, bb = ch["c"], ch["bbox"]
                    if c.isspace():
                        if cur:
                            words.append(cur)
                        cur = None
                        continue
                    if cur is None:
                        cur = dict(text=c, x0=bb[0], x1=bb[2], y0=bb[1],
                                   y1=bb[3], size=s["size"])
                    else:
                        cur["text"] += c
                        cur["x1"] = max(cur["x1"], bb[2])
                        cur["y0"] = min(cur["y0"], bb[1])
                        cur["y1"] = max(cur["y1"], bb[3])
                if cur:
                    words.append(cur)
    out = []
    for w in words:
        if w["size"] < modal * 0.85 and BARE_INT_RE.match(w["text"]):
            continue                      # superscript footnote reference
        w["ym"] = (w["y0"] + w["y1"]) / 2.0
        out.append(w)
    return out


def group_lines(words, tol=4.0):
    """Group words into baselines. Row pitch is ~16pt; the index/name offset is
    ~3pt, so a 4pt tolerance re-attaches the index without merging two rows."""
    out = []
    for w in sorted(words, key=lambda w: (w["ym"], w["x0"])):
        if out and abs(w["ym"] - out[-1]["ym"]) <= tol:
            out[-1]["words"].append(w)
            out[-1]["ym"] = (out[-1]["ym"] * (len(out[-1]["words"]) - 1)
                             + w["ym"]) / len(out[-1]["words"])
        else:
            out.append(dict(ym=w["ym"], words=[w]))
    for l in out:
        l["words"].sort(key=lambda w: w["x0"])
        l["text"] = re.sub(r"\s+", " ", " ".join(w["text"] for w in l["words"])).strip()
    return out


# --- zone classification -----------------------------------------------------
# The EXHIBIT NUMBER IS NOT STABLE. Through the 2010s the payer table is
# Exhibit 3 and the fund condition statement is Exhibit 2; by the 2020s the
# payer table is Exhibit 2 and the fund condition statement is Exhibit 3.
# Keying on the number would have swapped a money table for a balance sheet
# halfway through the series. Zones are classified by their own header text.
ZONE_RULES = [
    ("fund_condition", re.compile(r"FUND\s+CONDITION\s+STATEMENT", re.I)),
    ("rstf_payer", re.compile(
        r"Amount of Revenue.*(from|Reported by)\s+Each\s+Compact|"
        r"Revenue\s+(Received|Reported)\s*$", re.I)),
    ("rstf_shortfall_by_tribe", re.compile(
        r"Aggregate Amount of Shortfalls", re.I)),
    ("rstf_recipient", re.compile(
        r"(Total Amount of Distribution|Amount of Funds\s+(to Be|Recommended)|"
        r"Eligible (Recipient Indian Tribe|to Receive)|RSTF Distribution List)",
        re.I)),
]
HEADER_STOP = re.compile(
    r"^(Attachment|APPENDIX|Footnotes?:|Page \d+|EXHIBIT \d+\s*$)", re.I)


def classify_zone(header_text):
    for name, pat in ZONE_RULES:
        if pat.search(header_text):
            return name
    return None


DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+(\d{1,2}),\s*(\d{4})", re.I)
MONTHS = {m.lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}


def _date_from_text(t):
    m = DATE_RE.search(t or "")
    if not m:
        return None
    return dt.date(int(m.group(3)), MONTHS[m.group(1).lower()],
                   int(m.group(2))).isoformat()


def _quarter_end_from_linktext(t):
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", t or "")
    if m:
        return dt.date(int(m.group(3)), int(m.group(1)),
                       int(m.group(2))).isoformat()
    return None


def _quarter_start(qe):
    y, m, _ = (int(x) for x in qe.split("-"))
    sm = m - 2
    if sm <= 0:
        sm += 12
        y -= 1
    return dt.date(y, sm, 1).isoformat()


def _fy_start(qe):
    y, m, _ = (int(x) for x in qe.split("-"))
    return dt.date(y if m >= 7 else y - 1, 7, 1).isoformat()


# --- column banding ---------------------------------------------------------
def band_columns(money_words, gap=18.0):
    """Cluster right edges into ordered columns.

    RIGHT edges, not left: a right edge is stable across digit counts and a
    left edge is not. This is the same rule that made the Michigan tables foot.
    """
    edges = sorted(w["x1"] for w in money_words)
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


def assign_band(w, centers):
    return min(range(len(centers)), key=lambda i: abs(w["x1"] - centers[i]))


TOTAL_RE = re.compile(r"^\s*(Grand\s+)?Totals?\b", re.I)
SKIP_LABEL_RE = re.compile(
    r"^\s*(Interest|Exhibit|EXHIBIT|Compact Tribe|Eligible|Recipient|"
    r"Non-Compact|Secretarial|"
    r"Quarterly|Total Potential|Distribution|Revenue|Amount|County|Footnote|"
    r"Page \d|No\.|TRIBE|Fiscal|Inception|Received|from|Through|Number of|"
    r"Quarters?)\b", re.I)
NAME_OK_RE = re.compile(r"[A-Za-z]{3}")


def parse_money_table(doc, link_text=""):
    """Walk a CGCC report and return zones of (label, [column values]) rows.

    Returns list of dicts: zone_type, header, page, rows, totals, columns.
    """
    # ZONES ARE ANCHORED ON AN "Exhibit N" LINE, NOT ON A PHRASE.
    #
    # The first version classified any line whose text looked like an exhibit
    # heading. Page 1 of every staff report is a memo whose SUBJECT line reads
    # "...Distribution of Funds to Non-Compact Tribes (Eligible Recipient Indian
    # Tribes) for the Quarter Ended June 30, 2006", and whose next paragraph
    # states "$10,839,371.91". That opened a zone on the memo and swept
    # narrative sentences in as data rows: 4,029 rows landed under an
    # unrecognised column layout and no zone footed. A zone now begins only at a
    # line that STARTS with "Exhibit N", and the exhibit's own repeated
    # page-headers merge into ONE table per type per document, so the printed
    # Totals row at the end of the table can foot the whole thing.
    EXH = re.compile(r"^\s*EXHIBIT\s+(\d+)\b", re.I)
    zmap = {}
    cur = None
    carry = ""
    for pno in range(doc.page_count):
        page = doc[pno]
        lines = group_lines(page_words(page))
        # A WRAPPED NAME NEVER CROSSES A PAGE BREAK, but the exhibit's column
        # header is reprinted on every page. Carrying text across the break
        # produced labels like "Recipient Indian Tribe Received Shortfall
        # Distribution September 30, 2008 Cortina Rancheria" and cost the
        # resolver the row.
        carry = ""
        for ln in lines:
            # Repair numbers the text layer split before anything reads them.
            ln["words"] = rejoin_split_money(ln["words"])
            ln["text"] = re.sub(
                r"\s+", " ", " ".join(w["text"] for w in ln["words"])).strip()
            txt = ln["text"]
            money = [w for w in ln["words"] if _is_money(w["text"])]
            dashes = [w for w in ln["words"] if _is_dash(w["text"])]
            nonmoney = [w for w in ln["words"]
                        if not _is_money(w["text"]) and not _is_dash(w["text"])]
            label = re.sub(r"\s+", " ", " ".join(w["text"] for w in nonmoney)).strip()
            label = re.sub(r"^\d{1,3}\s+", "", label).strip()

            if EXH.match(txt) and not money:
                cur = dict(pending_header=[txt], zone_type=None, page=pno + 1)
                carry = ""
                continue
            if cur is None:
                continue
            if cur["zone_type"] is None:
                # still reading the exhibit's caption
                if not money:
                    cur["pending_header"].append(txt)
                    zt = classify_zone(" ".join(cur["pending_header"]))
                    if zt:
                        cur["zone_type"] = zt
                        z = zmap.get(zt)
                        if z is None:
                            z = dict(zone_type=zt, page_first=cur["page"],
                                     header_lines=[], rows=[], totals=[],
                                     money_words=[])
                            zmap[zt] = z
                        for h in cur["pending_header"]:
                            if h not in z["header_lines"] and len(z["header_lines"]) < 14:
                                z["header_lines"].append(h)
                        cur["zone"] = z
                    elif len(cur["pending_header"]) > 8:
                        cur = None
                continue
            z = cur["zone"]
            if HEADER_STOP.match(txt):
                cur = None
                carry = ""
                continue
            if not money and dashes and (z["rows"] or carry):
                full = re.sub(r"\s+", " ", (carry + " " + label)).strip()
                full = re.sub(r"^\d{1,3}\s+", "", full).strip()
                quote = ((carry + " ") if carry else "") + txt
                carry = ""
                if NAME_OK_RE.search(full) and not SKIP_LABEL_RE.match(full):
                    z["rows"].append(dict(label=full, money=[], page=pno + 1,
                                          line_text=quote, suppressed=True))
                continue
            if not money:
                # A TRIBE NAME THAT WRAPS TO A SECOND LINE PUTS ITS MONEY ON
                # THE SECOND LINE. `Bear River Band of the / Rohnerville
                # Rancheria  117,531.46 ...` read one line at a time labels the
                # payment "Rohnerville Rancheria" and loses "Bear River Band" -
                # and the resolver would then key the money to whatever
                # "Rohnerville Rancheria" alone resolves to. The unfinished
                # name is carried forward onto the line that carries numbers.
                if not z["rows"] and len(z["header_lines"]) < 14 and \
                        txt not in z["header_lines"]:
                    z["header_lines"].append(txt)
                elif (z["rows"] and NAME_OK_RE.search(txt)
                      and not SKIP_LABEL_RE.match(txt) and len(txt) < 80
                      and len(carry) < 80):
                    carry = (carry + " " + txt).strip()
                continue
            if z["zone_type"] == "fund_condition":
                carry = ""
                continue
            z["money_words"].extend(money)
            full = re.sub(r"\s+", " ", (carry + " " + label)).strip()
            full = re.sub(r"^\d{1,3}\s+", "", full).strip()
            quote = ((carry + " ") if carry else "") + txt
            carry = ""
            # The carry is resolved BEFORE the total test. Without that, a row
            # whose name and numbers sit on baselines more than the grouping
            # tolerance apart arrives with an empty label and reads as a Totals
            # row - which is how `Cahuilla Band of Indians 0.00 125,000.00`
            # became the printed total of Exhibit 2 and failed 20 zones.
            if TOTAL_RE.match(full) or not full:
                z["totals"].append(dict(label=full or "Total", money=money,
                                        page=pno + 1))
                continue
            if not NAME_OK_RE.search(full) or SKIP_LABEL_RE.match(full):
                continue
            z["rows"].append(dict(label=full, money=money, page=pno + 1,
                                  line_text=quote, suppressed=False))
    zones = list(zmap.values())

    for z in zones:
        centers = band_columns(z["money_words"])
        z["columns"] = centers
        for r in z["rows"] + z["totals"]:
            vals = [None] * len(centers)
            for w in r["money"]:
                if centers:
                    vals[assign_band(w, centers)] = _money_val(w["text"])
            r["values"] = vals
            r.setdefault("suppressed", False)
    return [z for z in zones if z["zone_type"] != "fund_condition" and z["rows"]]


def foot_zone(z):
    """Compare each column's row sum with the document's own printed Total.

    Returns (ok, detail). A zone with no printed total is `no_total` - reported,
    not silently trusted.
    """
    # `Totals $` - CGCC prints the currency symbol in its own cell, so it lands
    # in the label. Requiring a bare `Totals` sent 20 zones to compare against
    # `Grand Totals`, which adds interest income and is not the column sum.
    named = [t for t in z["totals"]
             if re.match(r"^\s*Totals?\s*\$?\s*$", t["label"], re.I)]
    # The LAST one. `Grand Totals` adds interest income and is not the column
    # sum; an earlier stray is a mis-read data row. Taking the first match put
    # `0.00 / 125,000.00` up against a $47.9M column.
    tot = named[-1] if named else (z["totals"][-1] if z["totals"] else None)
    if tot is None:
        return "no_total", ""
    # ROUNDING RESIDUE IS NOT A FAILED FOOTING, and refusing it discarded real
    # data. The 93rd report's Exhibit 2 sums to $61,300,403.81 against a
    # printed $61,300,404.81 over 62 tribes -- ONE DOLLAR, 1.6e-8 of the
    # total. That is the source's own per-row cent rounding accumulating, and
    # the strict test threw away all 62 payer rows for it.
    #
    # The relative test is what separates the two failure modes and it is why
    # this is safe: cent rounding is O(n x $0.01) and vanishes against the
    # total; a dropped row or a transposed digit does not. The 95th report's
    # $40,000 discrepancy (1,660,891,048.19 vs 1,660,851,048.19 - a
    # transposition) is 2.4e-5 relative and is STILL REFUSED, which is the
    # behaviour we want. Both bounds must hold.
    #
    # A column accepted this way is labelled `foots_within_rounding` on every
    # row it produces, so a subscriber can exclude it in one filter.
    n = max(len(z["rows"]), 1)
    detail, ok, used_tolerance = [], True, False
    for i in range(len(z["columns"])):
        s = round(sum(r["values"][i] or 0 for r in z["rows"]), 2)
        p = tot["values"][i] if i < len(tot["values"]) else None
        if p is None:
            detail.append(f"col{i}:no_printed_total")
            continue
        diff = abs(s - p)
        match = diff < 0.011
        near = (not match and diff <= 0.02 * n
                and diff / max(abs(p), 1.0) < 1e-7)
        if near:
            used_tolerance = True
            detail.append(f"col{i}:{s:,.2f}~={p:,.2f} "
                          f"(rounding residue {diff:,.2f} over {n} rows, "
                          f"{diff / max(abs(p), 1.0):.2e} of the total)")
            continue
        ok = ok and match
        detail.append(f"col{i}:{s:,.2f}{'==' if match else '!='}{p:,.2f}")
    status = ("foot_failed" if not ok else
              "foots_within_rounding" if used_tolerance else "foots")
    return status, "; ".join(detail)


# --- column header -> metric -------------------------------------------------
# Only headers we recognise become metrics. An unrecognised header is refused to
# the review queue: a well-formed row under a guessed metric name is worse than
# a queue item because it looks publishable.
def metric_for(zone_type, header_blob, col_idx, n_cols):
    h = re.sub(r"\s+", " ", header_blob).lower()
    if zone_type == "rstf_recipient":
        cols = ["rstf_distribution_from_revenue_received",
                "rstf_distribution_from_shortfall_transfer",
                "rstf_distribution_total",
                "rstf_distribution_inception_to_date"]
        # FIVE COLUMNS FROM THE 98th REPORT (quarter ended 2026-03-31) ON.
        # CGCC added an "Annual Distribution from Revenue Received" column
        # between the quarterly distribution and the shortfall. There was no
        # five-column mapping, so every column of every such exhibit was
        # refused as `unmapped_column` and the newest reports produced
        # nothing. The test is on the HEADER TEXT, not on the count alone --
        # a positional guess against an unrecognised five-column table is
        # exactly what this function exists to refuse.
        if n_cols == 5 and "annual distribution" in h:
            return ["rstf_distribution_from_revenue_received",
                    "rstf_distribution_annual_from_revenue_received",
                    "rstf_distribution_from_shortfall_transfer",
                    "rstf_distribution_total",
                    "rstf_distribution_inception_to_date"][col_idx]
        if n_cols == 4:
            return cols[col_idx]
        if n_cols == 3:
            return (cols[:3] if "inception" not in h
                    else [cols[0], cols[2], cols[3]])[col_idx]
        if n_cols == 2:
            return ([cols[2], cols[3]] if "inception" in h
                    else [cols[0], cols[2]])[col_idx]
        if n_cols == 1:
            return "rstf_distribution_total"
        return None
    if zone_type == "rstf_payer":
        if n_cols == 1:
            return "rstf_payment_received_fiscal_year_to_date"
        if n_cols == 2:
            return ["rstf_payment_received_fiscal_year_to_date",
                    "rstf_payment_received_inception_to_date"][col_idx]
        return None
    if zone_type == "rstf_shortfall_by_tribe":
        names = ["rstf_shortfall_total_potential_distribution",
                 "rstf_shortfall_total_approved_distribution",
                 "rstf_shortfall_aggregate"]
        # first numeric column in this table is "Quarters Eligible", a count
        if n_cols == 4:
            return (["quarters_eligible"] + names)[col_idx]
        if n_cols == 3:
            return names[col_idx]
        return None
    return None


# A cumulative figure published beside an annual one is a double count waiting
# to happen. Extract it, foot it, then withhold it by flag - never by deletion.
CUMULATIVE_METRICS = {"rstf_payment_received_inception_to_date",
                      "rstf_distribution_inception_to_date"}
COUNT_METRICS = {"quarters_eligible"}



# ===========================================================================
# document-level drivers
# ===========================================================================
def _manifest_rows():
    with open(MANIFEST, encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r["local_file"]]


def parse_rstf_documents():
    """RSTF quarterly distribution reports + the per-tribe shortfall exhibits."""
    out, zonelog = [], []
    for m in _manifest_rows():
        if m["doc_class"] not in ("rstf_quarterly_distribution",
                                  "rstf_shortfall_notification", "sdf_report",
                                  "other"):
            continue
        path = os.path.join(RAW, m["local_file"])
        try:
            doc = fitz.open(path)
        except Exception as e:
            zonelog.append(dict(file=m["local_file"], zone="",
                                status="unreadable_pdf", detail=str(e)[:120]))
            continue
        page1 = doc[0].get_text() if doc.page_count else ""
        try:
            zones = parse_money_table(doc, m["link_text"])
        except Exception as e:
            zonelog.append(dict(file=m["local_file"], zone="",
                                status="parse_error", detail=str(e)[:160]))
            doc.close()
            continue
        if not zones:
            zonelog.append(dict(file=m["local_file"], zone="",
                                status="no_money_zone", detail=""))
            doc.close()
            continue

        subj = re.search(r"Quarter Ended[^\r\n]*", page1)
        qe = (_quarter_end_from_linktext(m["link_text"])
              or _date_from_text(subj.group(0) if subj else "")
              or _date_from_text(page1[:1800]))
        for z in zones:
            hdr = " ".join(z["header_lines"])
            status, detail = foot_zone(z)
            n_cols = len(z["columns"])
            # CGCC's own link text ("Quarter Ended: 06/30/2026") is the most
            # reliable period statement; an in-document date can be the memo
            # date rather than the period end. Prefer a date that actually
            # falls on a quarter boundary.
            hdr_d = _date_from_text(hdr)
            zone_qe = hdr_d or qe
            if hdr_d and int(hdr_d[5:7]) not in (3, 6, 9, 12) and qe:
                zone_qe = qe
            fy = re.search(r"[Ff]iscal [Yy]ear (\d{4})-(\d{2,4})", hdr)
            zonelog.append(dict(file=m["local_file"], zone=z["zone_type"],
                                status=status,
                                detail=("rows=%d cols=%d period=%s %s"
                                        % (len(z["rows"]), n_cols, zone_qe,
                                           detail))[:400]))
            if status == "foot_failed":
                continue                      # refused: does not foot
            if not zone_qe:
                zonelog.append(dict(file=m["local_file"], zone=z["zone_type"],
                                    status="no_period", detail=hdr[:180]))
                continue
            for r in z["rows"]:
                for i in range(n_cols if not r.get("suppressed") else 1):
                    v = r["values"][i] if not r.get("suppressed") else ""
                    if v is None:
                        continue
                    metric = metric_for(z["zone_type"], hdr, i, n_cols)
                    if metric is None:
                        zonelog.append(dict(file=m["local_file"],
                                            zone=z["zone_type"],
                                            status="unmapped_column",
                                            detail="col%d/%d %s"
                                                   % (i, n_cols, hdr[:150])))
                        continue
                    if z["zone_type"] == "rstf_recipient":
                        ps, pe = _quarter_start(zone_qe), zone_qe
                        pbasis = "quarter"
                        direction = "paid_out"
                    elif z["zone_type"] == "rstf_payer":
                        ps, pe = _fy_start(zone_qe), zone_qe
                        pbasis = "fiscal_year_to_date"
                        direction = "paid_in"
                    else:
                        ps = (dt.date(int(fy.group(1)), 7, 1).isoformat()
                              if fy else _fy_start(zone_qe))
                        pe = zone_qe
                        pbasis = "fiscal_year"
                        direction = "paid_out"
                    out.append(dict(
                        fund="RSTF", direction=direction,
                        recipient_type="tribe",
                        party_name_as_published=r["label"],
                        metric=metric, value=v,
                        suppressed=("yes" if r.get("suppressed") else ""),
                        unit="count" if metric in COUNT_METRICS else "USD",
                        period_start=ps, period_end=pe, period_basis=pbasis,
                        source_file=m["local_file"], source_url=m["source_url"],
                        source_page=r["page"], source_quote=r["line_text"][:400],
                        source_document_type=m["doc_class"],
                        source_link_text=m["link_text"],
                        zone_header=re.sub(r"\s+", " ", hdr)[:300],
                        foot_status=status, foot_detail=detail[:300],
                        document_status=("revised" if re.search(
                            r"revis", m["link_text"] + m["local_file"], re.I)
                            else "original"),
                        issue_date="",
                        county="",
                        fetched_date=m["fetched_date"]))
        doc.close()
    return out, zonelog


TNGF_GRANT = [
    (re.compile(r"COVID", re.I), "covid19_emergency_grant"),
    (re.compile(r"Emergency Response", re.I), "emergency_response_grant"),
    (re.compile(r"Equal Distribution", re.I), "equal_distribution_grant"),
    (re.compile(r"Capacity Building", re.I), "capacity_building_grant"),
    (re.compile(r"Impact Grant", re.I), "impact_grant"),
]


def parse_tngf_documents():
    """Tribal Nation Grant Fund disbursement reports: tribe, title, amount."""
    out, log = [], []
    for m in _manifest_rows():
        blob = m["link_text"] + " " + m["local_file"]
        if ("Tribal Nation Grant Fund" not in m["link_text"]
                and m["doc_class"] != "tngf_report"):
            continue
        doc = fitz.open(os.path.join(RAW, m["local_file"]))
        fy = re.search(r"FY\s*(\d{4})/(\d{2,4})", m["link_text"])
        grant = next((g for p, g in TNGF_GRANT if p.search(blob)), "")
        printed_total = None
        recs = []
        for pno in range(doc.page_count):
            for ln in group_lines(page_words(doc[pno])):
                money = [w for w in ln["words"] if _is_money(w["text"])]
                if not money:
                    continue
                label = re.sub(r"\s+", " ", " ".join(
                    w["text"] for w in ln["words"]
                    if not _is_money(w["text"])
                    and w["x0"] < money[0]["x0"])).strip()
                label = re.sub(r"^\d{1,3}\s+", "", label).strip()
                if re.match(r"^\s*Total", label, re.I):
                    printed_total = max(_money_val(w["text"]) for w in money)
                    continue
                if not NAME_OK_RE.search(label):
                    continue
                dates = re.findall(r"\b\d{1,2}/\d{1,2}/\d{4}\b", ln["text"])
                amt = max(_money_val(w["text"]) for w in money)
                recs.append((label, amt, ln, pno + 1,
                             dates[-1] if dates else ""))
        s = round(sum(r[1] for r in recs), 2)
        if printed_total is None:
            status = "no_total"
        elif abs(s - printed_total) < 0.011:
            status = "foots"
        else:
            status = "foot_failed"
        log.append(dict(file=m["local_file"], zone="tngf", status=status,
                        detail="rows=%d sum=%.2f printed=%s"
                               % (len(recs), s, printed_total)))
        if status == "foot_failed":
            doc.close()
            continue
        for label, amt, ln, page, issued in recs:
            # "Tribe Name | Application Title | Awarded Amount": the tribe is
            # the leading clause. Splitting on the title would be a guess, so
            # the whole left cell is carried verbatim and the resolver decides.
            ps = ("%s-07-01" % fy.group(1)) if fy else ""
            pe = ("%d-06-30" % (int(fy.group(1)) + 1)) if fy else ""
            out.append(dict(
                fund="TNGF", direction="paid_out", recipient_type="tribe",
                party_name_as_published=label,
                metric=("tngf_" + grant) if grant else "tngf_grant_disbursement",
                value=amt, unit="USD",
                period_start=ps, period_end=pe, period_basis="fiscal_year",
                source_file=m["local_file"], source_url=m["source_url"],
                source_page=page, source_quote=ln["text"][:400],
                source_document_type="tngf_disbursement_report",
                source_link_text=m["link_text"],
                zone_header=m["link_text"][:300],
                foot_status=status,
                foot_detail="sum=%.2f printed=%s" % (s, printed_total),
                document_status="original", issue_date=issued, county="",
                fetched_date=m["fetched_date"]))
        doc.close()
    return out, log


COUNTY_RE = re.compile(
    r"^(Amador|Butte|Colusa|Del Norte|El Dorado|Fresno|Glenn|Humboldt|Imperial|"
    r"Inyo|Kings|Lake|Lassen|Madera|Mendocino|Modoc|Mono|Monterey|Napa|Placer|"
    r"Plumas|Riverside|Sacramento|San Bernardino|San Diego|San Joaquin|"
    r"Santa Barbara|Shasta|Siskiyou|Sonoma|Sutter|Tehama|Trinity|Tulare|"
    r"Tuolumne|Yolo|Yuba|Alpine|Calaveras|Kern|Marin|Mariposa|Nevada|Solano|"
    r"Stanislaus|Sierra)\s*$")


def parse_sdf_local_mitigation():
    """SDF local mitigation grants, from the 2015 JLBC report's appendices.

    THE BRIEF EXPECTED THESE TO NAME THE TRIBE WHOSE FACILITY GENERATED THEM.
    THEY DO NOT. Every appendix row is county -> local agency -> project ->
    amount. No tribe appears anywhere in the tables. Attaching a Riverside
    County fire-district grant to a tribe would be an inference from geography
    and nothing else, so the rows publish with a blank tribe and an explicit
    reason, and are never summed with RSTF.
    """
    out, log = [], []
    m = next((r for r in _manifest_rows()
              if "SDF_Report_-_JLBC" in r["local_file"]), None)
    if m is None:
        return out, log
    doc = fitz.open(os.path.join(RAW, m["local_file"]))
    fy = county = None
    for pno in range(doc.page_count):
        if pno < 36:                     # narrative section; appendices follow
            continue
        for ln in group_lines(page_words(doc[pno])):
            t = ln["text"]
            fym = re.search(r"FY\s*(\d{4})/(\d{2})\b", t)
            if fym:
                fy = fym.group(0)
            # THE COUNTY IS ON THE SUB-TABLE'S HEADER ROW, NOT ON A LINE OF ITS
            # OWN. `County  FY 2003/04  Amador  For:  Amount Paid  Amt
            # Allocated  Amt Reverted` is one baseline; a rule that expected a
            # bare county name matched nothing and the appendix yielded zero
            # rows. Each `Amount Paid` header opens a new county sub-table.
            if re.search(r"Amount\s+Paid", t, re.I):
                head = re.sub(r"FY\s*\d{4}/\d{2}", " ", t)
                head = re.sub(r"\b(County|For:|Amount\s+Paid|Amt\s+Allocated|"
                              r"Amt\s+Reverted)\b", " ", head, flags=re.I)
                head = re.sub(r"\s+", " ", head).strip()
                cm = COUNTY_RE.match(head)
                if cm:
                    county = cm.group(1)
                continue
            cm = COUNTY_RE.match(t.strip())
            if cm:
                county = cm.group(1)
                continue
            money = [w for w in ln["words"] if _is_money(w["text"])]
            if not money or not fy or not county:
                continue
            left = [w for w in ln["words"]
                    if not _is_money(w["text"]) and w["x0"] < money[0]["x0"]]
            label = re.sub(r"\s+", " ",
                           " ".join(w["text"] for w in left)).strip()
            if not NAME_OK_RE.search(label):
                continue
            if re.match(r"^\s*(Total|County|For:|Amount|Amt)\b", label, re.I):
                continue
            y1 = int(fy[3:7])
            out.append(dict(
                fund="SDF", direction="paid_out",
                recipient_type="local_government_agency",
                party_name_as_published=label, county=county,
                metric="sdf_local_mitigation_grant_amount_paid",
                value=_money_val(money[0]["text"]), unit="USD",
                period_start="%d-07-01" % y1, period_end="%d-06-30" % (y1 + 1),
                period_basis="fiscal_year",
                source_file=m["local_file"], source_url=m["source_url"],
                source_page=pno + 1, source_quote=t[:400],
                source_document_type="sdf_jlbc_report_appendix",
                source_link_text=m["link_text"],
                zone_header=("Appendix - SDF Funding for Local Mitigation "
                             "Grants %s, County of %s" % (fy, county)),
                foot_status="county_subtotal_printed", foot_detail="",
                document_status="original", issue_date="",
                fetched_date=m["fetched_date"]))
    log.append(dict(file=m["local_file"], zone="sdf_local_mitigation",
                    status="parsed", detail="rows=%d" % len(out)))
    doc.close()
    return out, log


# ===========================================================================
# STAGE 4 - facilities.  CGCC's rosters: tribe <-> casino <-> city <-> county.
# ===========================================================================
def _spans(page):
    """Cell-level spans with exact boxes and font size.

    The CGCC rosters set each table CELL as one span, so spans are the right
    unit here - word-level reading would have to guess where a wrapped tribe
    name ends and the casino name begins. The row number is a 4.8pt span in its
    own column while the body is 7.2pt, which is what delimits a record.
    """
    out = []
    for b in page.get_text("rawdict")["blocks"]:
        for l in b.get("lines", []):
            for s in l["spans"]:
                txt = "".join(c["c"] for c in s.get("chars", []))
                if not txt.strip():
                    continue
                x0, y0, x1, y1 = s["bbox"]
                out.append(dict(text=txt.strip(), x0=x0, x1=x1,
                                ym=(y0 + y1) / 2.0, size=round(s["size"], 2)))
    return out


def _col_starts(xs, gap=20.0):
    xs = sorted(xs)
    if not xs:
        return []
    cols, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] > gap:
            cols.append(cur)
            cur = [x]
        else:
            cur.append(x)
    cols.append(cur)
    return [min(c) for c in cols]


# COLUMNS ARE NAMED FROM THE PRINTED HEADER, NOT FROM THEIR ORDINAL POSITION.
# The three rosters do not share a column count - the RSTF-eligible list has no
# fund columns, the payer list has two - and a wrapped cell can open a spurious
# column start. Reading the Nth column as "city" because it was third put every
# casino name under `casino_county` in one file and left `casino_city` empty in
# another. Each header is centred over its column, so a column is named by the
# header whose centre is nearest the column's own x mid-range.
# Tested in THIS order, and the order is the point. A two-line header is
# reassembled by x-centre, so "CASINO" over "COUNTY" can arrive as either
# "CASINO COUNTY" or "COUNTY CASINO"; anchored whole-string patterns matched
# neither, the county column went unnamed, and county text merged into city.
# Token tests, most specific first.
ROSTER_HEADER_FIELDS = [
    (re.compile(r"REVENUE\s*SHARING|\bRSTF\b", re.I), "rstf"),
    (re.compile(r"SPECIAL\s*DISTRIBUTION|\bSDF\b", re.I), "sdf"),
    (re.compile(r"\bCOUNTY\b", re.I), "county"),
    (re.compile(r"\bCITY\b", re.I), "city"),
    (re.compile(r"\bTRIBE\b", re.I), "tribe"),
    (re.compile(r"\bCASINO\b", re.I), "casino"),
]


def _header_groups(spans, first_bound):
    """Printed header labels with their centres, multi-line headers joined."""
    heads = [s for s in spans if s["ym"] < first_bound - 10]
    groups = []
    for s in sorted(heads, key=lambda s: ((s["x0"] + s["x1"]) / 2, s["ym"])):
        c = (s["x0"] + s["x1"]) / 2
        if groups and abs(c - groups[-1]["c"]) < 22:
            groups[-1]["t"] += " " + s["text"]
            groups[-1]["c"] = (groups[-1]["c"] + c) / 2
        else:
            groups.append(dict(c=c, t=s["text"]))
    named = []
    for g in groups:
        txt = re.sub(r"\s+", " ", g["t"]).strip()
        for pat, field in ROSTER_HEADER_FIELDS:
            if pat.search(txt):
                named.append((g["c"], field))
                break
    return named


def _assign_fields(body, named):
    """Two passes: seed from the header centres, then snap to the LEFT EDGES
    the data itself reveals.

    A header is centred over its column while the cell text is left-aligned, so
    centre-distance alone puts a short county name ("Inyo") almost equidistant
    between the city and county headers. Pass 1 uses the header centres only to
    discover where each column actually starts; pass 2 assigns every span by
    that learned left edge, which is unambiguous.
    """
    if not named:
        return {}
    seed = {}
    for s in body:
        c = (s["x0"] + s["x1"]) / 2
        # lint-ok: class7 - `id()` here is PYTHON OBJECT IDENTITY for an in-memory object,
        # used as a key in a dict/set that lives and dies inside this one function. It is
        # never written to a file, nothing joins on it, and it is not a primary key.
        # 293_lint_bug_classes.py waives the same shape in its own source. Triaged LOW by
        # 326_triage_class7_key_risk.py on 2026-08-26: no clean or spine table carries it.
        seed[id(s)] = min(named, key=lambda nf: abs(nf[0] - c))[1]
    lefts = {}
    for s in body:
        # lint-ok: class7 - `id()` here is PYTHON OBJECT IDENTITY for an in-memory object,
        # used as a key in a dict/set that lives and dies inside this one function. It is
        # never written to a file, nothing joins on it, and it is not a primary key.
        # 293_lint_bug_classes.py waives the same shape in its own source. Triaged LOW by
        # 326_triage_class7_key_risk.py on 2026-08-26: no clean or spine table carries it.
        f = seed[id(s)]
        lefts[f] = min(lefts.get(f, 1e9), s["x0"])
    order = sorted(lefts.items(), key=lambda kv: kv[1])
    out = {}
    for s in body:
        f = order[0][0]
        for fld, x in order:
            if s["x0"] >= x - 3:
                f = fld
        # lint-ok: class7 - `id()` here is PYTHON OBJECT IDENTITY for an in-memory object,
        # used as a key in a dict/set that lives and dies inside this one function. It is
        # never written to a file, nothing joins on it, and it is not a primary key.
        # 293_lint_bug_classes.py waives the same shape in its own source. Triaged LOW by
        # 326_triage_class7_key_risk.py on 2026-08-26: no clean or spine table carries it.
        out[id(s)] = f
    return out


def parse_cgcc_rosters():
    """CGCC's rosters: tribe <-> casino <-> city <-> county, and the payer matrix.

    CGCC publishes three dated rosters. They carry NO numeric capacity of any
    kind - no device counts, no revenue - so nothing here is a measurement and
    `measurement_type` stays blank on purpose. What they do carry is identity
    and, in the payments list, WHICH FUND EACH TRIBE PAYS INTO, which is the
    contributor side of California's transfer and the half nobody publishes
    elsewhere.
    """
    facs, log = [], []
    wanted = {"cgcc_casino_list", "cgcc_rstf_eligible_list",
              "cgcc_paying_tribes_list"}
    for m in _manifest_rows():
        if m["doc_class"] not in wanted:
            continue
        doc = fitz.open(os.path.join(RAW, m["local_file"]))
        as_of, n_rec = "", 0
        for pno in range(doc.page_count):
            sp = _spans(doc[pno])
            if not sp:
                continue
            sizes = Counter(round(s["size"], 1) for s in sp)
            modal = sizes.most_common(1)[0][0]
            if not as_of:
                for s in sp:
                    mm = re.search(r"as of\s+(.+)$", s["text"], re.I)
                    if mm:
                        as_of = _date_from_text(mm.group(1)) or ""
            body = [s for s in sp if s["size"] >= modal * 0.9]
            idx = [s for s in sp if s["size"] < modal * 0.9
                   and re.match(r"^\d{1,3}$", s["text"])]
            if not idx:
                continue
            left = min(s["x0"] for s in idx)
            idx = [s for s in idx if s["x0"] < left + 20]
            bounds = sorted(s["ym"] for s in idx)
            # THE TABLE BODY ONLY. Over the whole page the centred masthead
            # ("CALIFORNIA GAMBLING CONTROL COMMISSION") contributes four more
            # x positions, and treating those as columns shifted every cell.
            named = _header_groups(sp, bounds[0])
            body = [s for s in body if s["ym"] >= bounds[0] - 10
                    and s["x0"] > left + 2]
            fmap = _assign_fields(body, named)
            if not fmap:
                continue
            recs = [defaultdict(list) for _ in bounds]
            for s in body:
                j = -1
                for k, b in enumerate(bounds):
                    if s["ym"] >= b - 10:
                        j = k
                if j < 0:
                    continue
                # lint-ok: class7 - `id()` here is PYTHON OBJECT IDENTITY for an in-memory object,
                # used as a key in a dict/set that lives and dies inside this one function. It is
                # never written to a file, nothing joins on it, and it is not a primary key.
                # 293_lint_bug_classes.py waives the same shape in its own source. Triaged LOW by
                # 326_triage_class7_key_risk.py on 2026-08-26: no clean or spine table carries it.
                recs[j][fmap[id(s)]].append(s)
            for rec in recs:
                if not rec:
                    continue
                cell = {}
                for fld, ss in rec.items():
                    ss.sort(key=lambda s: (s["ym"], s["x0"]))
                    lines, last = [], None
                    for s in ss:
                        if last is not None and abs(s["ym"] - last) < 4:
                            lines[-1] = (lines[-1][0], (lines[-1][1] + " "
                                                        + s["text"]).strip())
                        else:
                            lines.append((s["ym"], s["text"]))
                        last = s["ym"]
                    cell[fld] = lines
                lines_of = lambda fld: [x[1] for x in cell.get(fld, [])]
                tribe = re.sub(r"\s+\d(\s*,\s*\d)*$", "",
                               " ".join(lines_of("tribe"))).strip()
                if not tribe or re.match(r"^(No\.|TRIBE|CASINO|CITY|COUNTY)$",
                                         tribe, re.I):
                    continue
                n_rec += 1
                fl_cols = sorted(f for f in rec if f in ("sdf", "rstf"))
                flags = " ".join(x[1] for f in ("sdf", "rstf")
                                 for x in cell.get(f, [])).strip()
                # A RECORD MAY LIST SEVERAL CASINOS, AND A CASINO NAME MAY WRAP.
                # Counting lines cannot tell those apart: Agua Caliente lists
                # three casinos, the second of which wraps, so the casino cell
                # has four lines against the city cell's three - and pairing by
                # index shifted every casino onto the next casino's city.
                # Casinos are cut on the CITY column's baselines instead: a
                # casino line with no city on its own baseline is a
                # continuation of the line above it.
                casl = cell.get("casino", []) or [(0.0, "")]
                ctyl = cell.get("city", []) or [(0.0, "")]
                cntl = cell.get("county", []) or [(0.0, "")]
                units = []
                if len(ctyl) > 1 and len(casl) >= len(ctyl):
                    near = lambda y: min(range(len(ctyl)),
                                         key=lambda i: abs(ctyl[i][0] - y))
                    buck = [[] for _ in ctyl]
                    cbuck = [[] for _ in ctyl]
                    for y, txt2 in casl:
                        buck[near(y)].append(txt2)
                    for y, txt2 in cntl:
                        cbuck[near(y)].append(txt2)
                    for ci, (cy, ctext) in enumerate(ctyl):
                        units.append((" ".join(buck[ci]).strip(), ctext,
                                      " ".join(cbuck[ci]).strip()))
                    alignment = "split_on_nearest_city_baseline"
                else:
                    units = [(" ".join(x[1] for x in casl).strip(),
                              " ".join(x[1] for x in ctyl).strip(),
                              " ".join(x[1] for x in cntl).strip())]
                    alignment = ("single_casino" if len(ctyl) <= 1
                                 else "joined_no_city_baselines")
                # A SPLIT THAT PRODUCES A FACILITY NAMED AFTER ITS OWN CITY IS
                # WRONG. Agua Caliente lists three casinos whose name lines lead
                # the city lines by more than one baseline, and the nearest-
                # baseline pairing still slips by one, yielding a casino called
                # "Rancho Mirage". Rather than publish a property that does not
                # exist, the whole record is emitted once, unsplit, and queued.
                if len(units) > 1 and any(
                        (not c) or _norm_fac(c) == _norm_fac(city)
                        for c, city, _ in units):
                    units = [(" | ".join(x[1] for x in casl),
                              " | ".join(x[1] for x in ctyl),
                              " | ".join(x[1] for x in cntl))]
                    alignment = "multi_casino_unsplit_needs_ruling"
                cas, cty, cnt = zip(*units) if units else ([""], [""], [""])
                aligned = True
                for k in range(len(units)):
                    facs.append(dict(
                        list_type=m["doc_class"], as_of_date=as_of,
                        tribe_name_as_published=tribe,
                        facility_name_as_published=cas[k],
                        casino_city=cty[k],
                        casino_county=cnt[k],
                        fund_flag_text=flags,
                        fund_flag_columns=",".join(fl_cols),
                        row_alignment=alignment,
                        source_file=m["local_file"], source_url=m["source_url"],
                        source_page=pno + 1,
                        source_quote=("%s | %s | %s | %s"
                                      % (tribe, cas[k], cty[k], cnt[k]))[:400],
                        source_link_text=m["link_text"],
                        fetched_date=m["fetched_date"]))
        doc.close()
        log.append(dict(file=m["local_file"], zone=m["doc_class"],
                        status="parsed",
                        detail="records=%d as_of=%s" % (n_rec, as_of)))
    return facs, log


# ===========================================================================
# STAGE 5 - resolve.  ONE resolver, plus refusals. Never a second matcher.
# ===========================================================================
SPINE_PATH = os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv")
COLLISIONS = os.path.join(REVIEW, "spine_short_name_collisions_2026-08-07.csv")
FACILITIES = os.path.join(CLEAN, "gaming_facilities.csv")
TERMS = os.path.join(CLEAN, "compact_structured_terms.csv")

# States a California gaming payment may legitimately resolve into. Three
# California tribes are administratively seated across a line (Colorado River,
# Fort Mojave, Quechan); everything else is a cross-state match and is refused,
# because `Indian Pueblo Cultural Center` (NM) -> `Makaha` (HI) already
# happened once in this repo.
ALLOWED_STATES = {"CA", "AZ", "NV", "OR", ""}

GENERIC_TOKENS = {
    "band", "tribe", "tribes", "nation", "indians", "indian", "of", "the",
    "california", "rancheria", "reservation", "community", "colony", "group",
    "mission", "valley", "band's", "paiute", "pomo", "miwok", "me-wuk",
    "previously", "listed", "as", "and", "a", "an",
}


def _read(p, enc="utf-8-sig"):
    with open(p, encoding=enc, newline="") as f:
        return list(csv.DictReader(f))


def load_spine_view():
    """The spine, with `fr_official_name` folded into `aliases`.

    This is NOT a second matcher. `resolve_entity` already consults aliases;
    the spine simply stores the Federal Register long form in its own column
    and CGCC writes that long form. Making it an alias hands the one resolver
    the data it already knows how to use. AGENTS.md: 161 entities carry a 1-2
    word canonical name expanding to a 5+ word official name.
    """
    spine = _read(SPINE_PATH)
    for r in spine:
        extra = [r.get("fr_official_name", "")]
        r["aliases"] = "|".join(
            [a for a in ([r.get("aliases", "")] + extra) if a and a.strip()])
    return spine


# tribe_id -> cedar_uid, read once. See the note on PAY_FIELDS.
_UID_BY_TRIBE_ID = {r["tribe_id"]: (r.get("cedar_uid") or "")
                    for r in _read(SPINE_PATH)}


def _tokens(s):
    s = re.sub(r"\(.*?\)", " ", s or "")
    return {t for t in re.split(r"[^A-Za-z']+", s.lower()) if len(t) > 2}


def _distinctive(s):
    return _tokens(s) - GENERIC_TOKENS - set(NAME_TRAPS)


class TribeResolver:
    def __init__(self):
        self.spine = load_spine_view()
        self.by_id = {r["tribe_id"]: r for r in self.spine}
        self.collision_ids = {r["tribe_id"] for r in _read(COLLISIONS)} \
            if os.path.exists(COLLISIONS) else set()
        self.cache = {}
        self.reasons = Counter()

    def resolve(self, raw):
        name = re.sub(r"\s+", " ", (raw or "")).strip()
        # CGCC prints "X (previously listed as Y)". The current name is the
        # claim; the parenthetical is the regulator's own note about a rename.
        name = re.sub(r"\s*\(previously listed as.*$", "", name, flags=re.I)
        name = re.sub(r"\s*\(.*?\)\s*$", "", name).strip().rstrip(",;*")
        if name in self.cache:
            return self.cache[name]
        tid, canon, how = resolve_entity(name, self.spine)
        res = dict(tribe_id="", tribe_canonical_name="", match_method=how,
                   entity_tier="", refusal="")
        if not tid:
            self.reasons[how.split(":")[0]] += 1
            res["refusal"] = how
            self.cache[name] = res
            return res
        ent = self.by_id[tid]
        cls = ent.get("entity_class", "")
        st = (ent.get("state") or "").strip()
        if cls in REFUSED_ENTITY_CLASSES:
            res["refusal"] = "refused_entity_class:%s" % cls
        elif st not in ALLOWED_STATES:
            res["refusal"] = "refused_cross_state:%s" % st
        elif how == "containment" and not (
                _distinctive(ent["canonical_name"]) <= _distinctive(name)):
            # The record must be at least as specific as the entity. This is
            # the guard that stops `CHICKASAW NATION` -> Children's Village.
            res["refusal"] = "refused_containment_not_more_specific"
        elif how == "containment" and tid in self.collision_ids and not (
                _distinctive(ent.get("fr_official_name") or "")
                and _distinctive(ent.get("fr_official_name") or "")
                <= _distinctive(name)):
            # NARROWED, AND THE NARROWING WAS MEASURED. Refusing every
            # containment match onto one of the spine's 281 short-name
            # collisions refused 472 California names outright - Bear River,
            # Cahto, Augustine, La Posta, Ramona, Scotts Valley - because the
            # collision list is exactly the set of tribes whose canonical name
            # is one or two words, which in California is most of them. The
            # collision is only dangerous when the record does not say WHICH
            # of the colliding entities it means. So the refusal now applies
            # only where the record fails to carry the entity's own Federal
            # Register long-form tokens: "Bear River Band of the Rohnerville
            # Rancheria" carries them and resolves; a bare "Bear River" does
            # not and is refused.
            res["refusal"] = "refused_short_name_collision"
        if res["refusal"]:
            self.reasons[res["refusal"].split(":")[0]] += 1
            self.cache[name] = res
            return res
        res.update(tribe_id=tid, tribe_canonical_name=ent["canonical_name"],
                   entity_tier="B")     # algorithmic; spec 10.1 lands at B
        self.reasons["resolved_" + how] += 1
        self.cache[name] = res
        return res


def _norm_fac(s):
    s = (s or "").lower()
    s = re.sub(r"&", " and ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\b(the|a|an)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


class FacilityResolver:
    """Exact normalised name within CA, or the tribe's sole CA property.

    There is no third tier, on purpose. A regulator name that matches nothing
    goes to the queue with the tribe's CA properties listed as candidates - it
    is never snapped to the nearest one.
    """

    def __init__(self):
        self.f = [r for r in _read(FACILITIES) if r.get("state") == "CA"]
        self.by_name = defaultdict(list)
        self.by_tribe = defaultdict(list)
        for r in self.f:
            self.by_name[_norm_fac(r["facility_name"])].append(r)
            if r.get("tribe_id"):
                self.by_tribe[r["tribe_id"]].append(r)

    def resolve(self, casino_name, tribe_id):
        n = _norm_fac(casino_name)
        if not n or n in ("n a", "na"):
            return "", "", "no_facility_named"
        hits = self.by_name.get(n, [])
        if len(hits) == 1:
            return hits[0]["facility_id"], hits[0]["facility_name"], "exact_name_in_state"
        if len(hits) > 1:
            return "", "", "ambiguous_exact_name:%d" % len(hits)
        own = self.by_tribe.get(tribe_id, [])
        if tribe_id and len(own) == 1:
            return own[0]["facility_id"], own[0]["facility_name"], "sole_property_of_tribe_in_state"
        cands = " | ".join("%s=%s" % (r["facility_id"], r["facility_name"])
                           for r in own[:6])
        return "", "", "unresolved_facility_name" + (":%s" % cands if cands else "")


# ---------------------------------------------------------------------------
# compact invertibility - checked against the parse, never assumed
# ---------------------------------------------------------------------------
RSTF_OR_TNGF = re.compile(
    r"Revenue\s+Sharing\s+Trust\s+Fund\s+or\s+the\s+Tribal\s+Nation\s+Grant\s+Fund",
    re.I)

# THE CALIFORNIA MARGINAL-BASE GUARD, AND THE DEFECT THAT FORCED IT.
#
# `compact_structured_terms.csv` marks 51 California rate rows
# `INVERTIBLE_FLAT_RATE` - correctly, by its own test: one rate, no bracket
# table, no per-device component in the clause. Dividing an RSTF receipt by
# that rate produced numbers that looked like tribe revenue. Reading the
# retained quotes one by one showed every single one of them is a MARGINAL
# base:
#
#   "six percent (6.0%) of its Net Win from the operation of Gaming Devices
#    IN EXCESS OF three hundred fifty (350)"
#   "an annual payment of thirty-six million, seven hundred thousand dollars
#    ($36,700,000.00); AND an annual payment for the operation of the
#    ADDITIONAL Gaming Devices ... fifteen percent (15%) of the Net Win"
#
# The rate applies to the win from devices above a threshold, and in the 15%
# instruments it sits beside a fixed annual sum. `payment / rate` therefore
# recovers the win on the marginal devices only - not the tribe's Net Win -
# and there is no published device count that would let anyone gross it up.
# California's device licences come from a statewide draw pool, so even the
# authorised count is an entitlement, not a floor.
#
# Publishing that quotient as tribe revenue would have understated the largest
# operators by an order of magnitude while carrying a verbatim citation. The
# guard refuses the derivation and names what blocks it; the payment itself
# still publishes, which is what California actually discloses.
MARGINAL_BASE = re.compile(
    r"in\s+excess\s+of|additional\s+Gaming\s+Devices|"
    r"annual\s+payment\s+of\s+\w+[^.]{0,80}\$|"
    r"Gaming\s+Devices\s+(above|over)\s|"
    r"more\s+than\s+[\w\s,()\-]{0,60}Gaming\s+Devices\s+but\s+fewer",
    re.I)


class CompactRates:
    def __init__(self):
        rows = [r for r in _read(TERMS) if r.get("state") == "California"]
        self.by_tribe = defaultdict(list)
        for r in rows:
            if r["term_field"] in ("revenue_sharing_rate", "machine_based_payment",
                                   "progressive_rate_schedule"):
                self.by_tribe[r["tribe_id"]].append(r)
        self.n_terms = len(rows)

    def governing(self, tribe_id, on_date):
        """The latest-effective rate terms at or before `on_date`."""
        cand = [r for r in self.by_tribe.get(tribe_id, [])
                if r["effective_from"] and r["effective_from"] <= on_date]
        if not cand:
            return []
        latest = max(r["effective_from"] for r in cand)
        return [r for r in cand if r["effective_from"] == latest]

    def assess(self, tribe_id, on_date):
        """Return (invertible, rate_pct, concept, base_scope, evidence, bound,
        source_url, quote). Conservative: any blocker means not invertible."""
        g = self.governing(tribe_id, on_date)
        if not g:
            return dict(invertible="no", rate="", concept="", base_scope="",
                        evidence="TRIBE_LEVEL_REVENUE",
                        bound="no_governing_compact_rate_term_on_file",
                        url="", quote="")
        rates = [r for r in g if r["term_field"] == "revenue_sharing_rate"]
        machine = [r for r in g if r["term_field"] == "machine_based_payment"]
        prog = [r for r in g if r["term_field"] == "progressive_rate_schedule"]
        inv = [r for r in rates if r["formula_invertibility"] == "INVERTIBLE_FLAT_RATE"]
        distinct = {r["value"] for r in inv}
        if not inv:
            return dict(invertible="no", rate="", concept="", base_scope="",
                        evidence="TRIBE_LEVEL_REVENUE",
                        bound="no_invertible_flat_rate_in_governing_instrument",
                        url=g[0]["source_url"], quote=g[0]["source_quote"][:400])
        if len(distinct) > 1 or prog:
            return dict(invertible="no", rate="", concept="", base_scope="",
                        evidence="BOUNDED_DERIVED_REVENUE",
                        bound="progressive_or_multi_rate_schedule",
                        url=inv[0]["source_url"], quote=inv[0]["source_quote"][:400])
        if machine:
            return dict(invertible="no", rate="", concept="", base_scope="",
                        evidence="BOUNDED_DERIVED_REVENUE",
                        bound="per_device_component_in_same_instrument",
                        url=inv[0]["source_url"], quote=inv[0]["source_quote"][:400])
        marg = [x for x in g if MARGINAL_BASE.search(x["source_quote"] or "")]
        if marg:
            return dict(invertible="no", rate=inv[0]["value"],
                        concept=inv[0]["revenue_concept"],
                        base_scope=inv[0]["base_scope"],
                        evidence="BOUNDED_DERIVED_REVENUE",
                        bound="marginal_base_rate_applies_only_to_net_win_from_"
                              "devices_above_a_stated_threshold",
                        url=inv[0]["source_url"],
                        quote=(inv[0]["source_quote"] or "")[:400])
        # THE RATE MUST GOVERN THE FUND THE PAYMENT WENT INTO. Tule River's
        # only surviving flat rate is 0.5% of net win into a local *Impact
        # Mitigation Fund*; dividing an RSTF receipt by it would cross two
        # different obligations. Concept preservation is a fund test too.
        if not any(re.search(r"Revenue\s+Sharing\s+Trust\s+Fund",
                             x["source_quote"] or "", re.I) for x in g):
            return dict(invertible="no", rate=inv[0]["value"],
                        concept=inv[0]["revenue_concept"],
                        base_scope=inv[0]["base_scope"],
                        evidence="BOUNDED_DERIVED_REVENUE",
                        bound="rate_governs_a_different_fund_than_the_payment",
                        url=inv[0]["source_url"],
                        quote=(inv[0]["source_quote"] or "")[:400])
        r = inv[0]
        # THE CALIFORNIA BLOCKER. The 2016-onward compacts read "pay ... for
        # deposit into the Revenue Sharing Trust Fund OR the Tribal Nation Grant
        # Fund". CGCC's exhibit reports RSTF receipts only, so RSTF / rate is a
        # LOWER BOUND on Net Win, not Net Win. A factual bound, with its basis
        # named - not a confidence interval, and no model is involved.
        split = any(RSTF_OR_TNGF.search(x["source_quote"] or "") for x in g)
        return dict(
            invertible=("bounded_below" if split else "yes"),
            rate=r["value"], concept=r["revenue_concept"],
            base_scope=r["base_scope"],
            evidence=("BOUNDED_DERIVED_REVENUE" if split else
                      ("TRIBE_LEVEL_REVENUE" if r["base_scope"] != "facility"
                       else "EXACT_DERIVED_PROPERTY_REVENUE")),
            bound=("rstf_receipts_only_compact_permits_deposit_into_rstf_or_tngf"
                   if split else ""),
            url=r["source_url"], quote=(r["source_quote"] or "")[:400])


# ===========================================================================
# STAGE 6 - emit
# ===========================================================================
PAY_FIELDS = [
    "payment_id", "fund", "direction", "recipient_type",
    # `cedar_uid` is THE HUB KEY and this build was erasing it. Measured
    # 2026-09-01 (workstream INT-2): `data/clean/ca_gaming_payments.csv` held
    # it populated on 35,730 rows, PAY_FIELDS did not list it, and this
    # rebuild dropped all 35,730 -- the class-6 silent column loss AGENTS.md
    # records for `144_build_admin_appeals.py` on the same day, in a second
    # file. Verified before the change: every populated `cedar_uid` equalled
    # the spine's `cedar_uid` for that row's `tribe_id`, 0 mismatches, so it
    # is DERIVED from the spine here rather than carried forward by hand.
    "cedar_uid",
    "tribe_id", "tribe_canonical_name", "party_name_as_published",
    "county", "metric", "value", "unit",
    "period_start", "period_end", "period_basis",
    "measurement_type", "value_suppressed_by_regulator", "revenue_evidence_class",
    "compact_rate_pct", "compact_revenue_concept", "compact_base_scope",
    "payment_invertible", "derived_tribe_revenue_value", "derived_revenue_scope",
    "bound_basis", "compact_term_source_url", "compact_term_source_quote",
    "confidence_tier", "entity_match_method", "entity_tier",
    "exclusion_flag", "exclusion_reason",
    "source_authority", "source_document_type", "source_url", "source_page",
    "source_quote", "source_link_text", "zone_header",
    "foot_status", "foot_detail", "document_status", "issue_date",
    "fetched_date", "built_date", "built_by_script",
]

FAC_FIELDS = [
    "record_id", "list_type", "as_of_date",
    # `cedar_uid` was DECLARED in this table's dataset contract and had never
    # been written. `62` reported it as a contract violation:
    # "ca_gaming_facilities_official.csv: declared join_cardinality names
    # column(s) not in the header: ['cedar_uid']". A contract that names a
    # join key the file does not carry is a promise to a buyer that the file
    # cannot keep. Added 2026-09-01 (INT-2), derived from the spine by
    # `tribe_id` exactly as it is on `ca_gaming_payments.csv`.
    "cedar_uid",
    "tribe_id", "tribe_canonical_name", "tribe_name_as_published",
    "facility_id", "facility_name", "facility_name_as_published",
    "facility_name_match_method", "casino_city", "casino_county",
    "pays_into_sdf", "pays_into_rstf", "rstf_eligible",
    "measurement_type", "confidence_tier", "entity_match_method", "entity_tier",
    "source_authority", "source_document_type", "source_url", "source_page",
    "source_quote", "fetched_date", "built_date", "built_by_script",
]

REVIEW_FIELDS = [
    "review_id", "issue_type", "fund", "name_as_published", "context",
    "evidence", "question", "candidate_entities", "source_url", "source_page",
    "source_quote", "YOUR_RULING",
]


def stage_build():
    print("[parse]")
    pay, log1 = parse_rstf_documents()
    print("  rstf/shortfall rows: %d" % len(pay))
    tngf, log2 = parse_tngf_documents()
    print("  tngf rows:           %d" % len(tngf))
    sdf, log3 = parse_sdf_local_mitigation()
    print("  sdf local rows:      %d  (NOT published - see below)" % len(sdf))
    # SDF LOCAL MITIGATION IS EXTRACTED AND DELIBERATELY NOT PUBLISHED.
    #
    # Two independent reasons, either of which is sufficient:
    #  1. NO TRIBE IS NAMED. The appendices are county -> local agency ->
    #     project -> amount. The brief expected these to name the tribe whose
    #     facility generated the payment; they do not. Attaching a Riverside
    #     County fire-district grant to a tribe would be an inference from
    #     geography alone.
    #  2. The line items DO NOT FOOT against the printed per-county totals in
    #     this pass. A three-column layout (Amount Paid / Amt Allocated / Amt
    #     Reverted) with a free-text purpose column defeats the leftmost-money
    #     rule, and several rows read 0.00 where the page shows a figure.
    # It is written to data/interim/ so the next pass starts from the parse
    # rather than from the retrieval, and the reason travels with the file.
    if sdf:
        with open(os.path.join(INTERIM,
                               "103_sdf_local_mitigation_unverified.csv"),
                  "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted(sdf[0].keys()))
            w.writeheader()
            w.writerows(sdf)
    n_sdf_withheld = len(sdf)
    sdf = []
    facs, log4 = parse_cgcc_rosters()
    print("  roster rows:         %d" % len(facs))
    zonelog = log1 + log2 + log3 + log4

    print("[resolve]")
    tr = TribeResolver()
    fr = FacilityResolver()
    cr = CompactRates()
    print("  spine=%d  CA facilities=%d  CA compact rate terms=%d"
          % (len(tr.spine), len(fr.f), cr.n_terms))

    review, out = [], []
    for i, r in enumerate(pay + tngf + sdf):
        row = {k: "" for k in PAY_FIELDS}
        row.update({k: v for k, v in r.items() if k in PAY_FIELDS})
        row["payment_id"] = "CAGP-%06d" % (i + 1)
        row["source_authority"] = "California Gambling Control Commission"
        row["measurement_type"] = (
            MeasurementType.REGULATORY_REPORTED_COUNT.value
            if r["unit"] == "USD" else MeasurementType.REGULATORY_REPORTED_COUNT.value)
        row["confidence_tier"] = Tier.B.value
        row["built_date"] = TODAY
        row["built_by_script"] = "code/103_build_california_gaming.py"

        if r.get("suppressed") == "yes":
            row["value_suppressed_by_regulator"] = "yes"
            row["exclusion_flag"] = "value_suppressed_by_regulator"
            row["exclusion_reason"] = (
                "CGCC prints `--` against this tribe and reports its figure "
                "only inside the report's `Aggregate Total for Tribes` line. "
                "The obligation and the period are published; the amount is "
                "not. Suppressed is not zero.")
        if re.match(r"^Aggregate Total", r["party_name_as_published"], re.I):
            r = dict(r, recipient_type="aggregate_of_suppressed_tribes")
            row["recipient_type"] = "aggregate_of_suppressed_tribes"
            row["exclusion_flag"] = row["exclusion_flag"] or "not_a_single_tribe"
            row["exclusion_reason"] = row["exclusion_reason"] or (
                "Combined figure for the tribes whose individual amounts CGCC "
                "suppresses. Kept because the report's Totals row foots only "
                "with it; never attributed to any tribe.")

        if r["recipient_type"] == "tribe":
            res = tr.resolve(r["party_name_as_published"])
            row["tribe_id"] = res["tribe_id"]
            row["cedar_uid"] = _UID_BY_TRIBE_ID.get(res["tribe_id"], "")
            row["tribe_canonical_name"] = res["tribe_canonical_name"]
            row["entity_match_method"] = res["match_method"]
            row["entity_tier"] = res["entity_tier"]
            if not res["tribe_id"]:
                review.append(dict(
                    review_id="CA-TRIBE:%s" % r["party_name_as_published"],
                    issue_type="agent_tribe_unresolved:%s" % res["refusal"],
                    fund=r["fund"], name_as_published=r["party_name_as_published"],
                    context="%s %s %s" % (r["fund"], r["direction"], r["metric"]),
                    evidence=r["zone_header"][:200],
                    question="Which spine entity is this CGCC tribe name?",
                    candidate_entities="", source_url=r["source_url"],
                    source_page=r["source_page"],
                    source_quote=r["source_quote"][:300], YOUR_RULING=""))
        else:
            row["entity_match_method"] = "not_a_tribe_local_government_agency"

        # --- revenue evidence -------------------------------------------------
        if r["fund"] == "RSTF" and r["direction"] == "paid_in" and row["tribe_id"]:
            a = cr.assess(row["tribe_id"], r["period_end"])
            row["compact_rate_pct"] = a["rate"]
            row["compact_revenue_concept"] = a["concept"]
            row["compact_base_scope"] = a["base_scope"]
            row["payment_invertible"] = a["invertible"]
            row["revenue_evidence_class"] = a["evidence"]
            row["bound_basis"] = a["bound"]
            row["compact_term_source_url"] = a["url"]
            row["compact_term_source_quote"] = a["quote"]
            # A CUMULATIVE PAYMENT DIVIDED BY A RATE IS A CUMULATIVE REVENUE.
            # Arithmetically fine, editorially a trap sitting beside annual
            # figures, so no derivation is written on an inception-to-date row.
            if (a["invertible"] in ("yes", "bounded_below") and a["rate"]
                    and r["metric"] not in CUMULATIVE_METRICS):
                try:
                    row["derived_tribe_revenue_value"] = round(
                        float(r["value"]) / (float(a["rate"]) / 100.0), 2)
                    row["derived_revenue_scope"] = (
                        "tribe" if a["base_scope"] != "facility" else "facility")
                except (ValueError, ZeroDivisionError):
                    row["derived_tribe_revenue_value"] = ""
        elif r["fund"] == "RSTF" and r["direction"] == "paid_in":
            row["revenue_evidence_class"] = "NO_REVENUE_OBSERVATION"
            row["bound_basis"] = "tribe_unresolved_no_compact_join"
        else:
            row["revenue_evidence_class"] = "NO_REVENUE_OBSERVATION"
            row["bound_basis"] = "payment_is_a_transfer_not_a_revenue_base"

        if r["metric"] in CUMULATIVE_METRICS:
            row["exclusion_flag"] = "cumulative_do_not_sum"
            row["exclusion_reason"] = (
                "Inception-to-date total. Published beside annual figures it is "
                "a double count; extracted and footed, withheld from any sum.")
        if r["fund"] == "SDF":
            row["exclusion_flag"] = row["exclusion_flag"] or "no_tribe_named_by_source"
            row["exclusion_reason"] = row["exclusion_reason"] or (
                "CGCC/SCO publish SDF local mitigation at county x local-agency x "
                "project. No tribe is named anywhere in the appendix, so the "
                "generating facility is not recoverable from this document.")
        out.append(row)

    # supersession: an original quarter republished as REVISED is flagged, not
    # deleted. Both remain readable; one filter separates them.
    revised = {(r["fund"], r["metric"], r["tribe_id"] or
                r["party_name_as_published"], r["period_end"])
               for r in out if r["document_status"] == "revised"}
    n_sup = 0
    for r in out:
        k = (r["fund"], r["metric"], r["tribe_id"] or r["party_name_as_published"],
             r["period_end"])
        if r["document_status"] == "original" and k in revised:
            r["exclusion_flag"] = r["exclusion_flag"] or "superseded_by_revised_report"
            r["exclusion_reason"] = r["exclusion_reason"] or (
                "CGCC republished this quarter as a REVISED staff report.")
            n_sup += 1

    # --- facilities -------------------------------------------------------
    frows, seen = [], {}
    for i, f in enumerate(facs):
        res = tr.resolve(f["tribe_name_as_published"])
        fid, fname, fmethod = fr.resolve(f["facility_name_as_published"],
                                         res["tribe_id"])
        row = {k: "" for k in FAC_FIELDS}
        row.update(dict(
            record_id="CAFAC-%05d" % (i + 1), list_type=f["list_type"],
            as_of_date=f["as_of_date"],
            cedar_uid=_UID_BY_TRIBE_ID.get(res["tribe_id"], ""),
            tribe_id=res["tribe_id"],
            tribe_canonical_name=res["tribe_canonical_name"],
            tribe_name_as_published=f["tribe_name_as_published"],
            facility_id=fid, facility_name=fname,
            facility_name_as_published=f["facility_name_as_published"],
            facility_name_match_method=fmethod,
            casino_city=f["casino_city"], casino_county=f["casino_county"],
            pays_into_sdf="", pays_into_rstf="",
            rstf_eligible=("yes" if f["list_type"] == "cgcc_rstf_eligible_list"
                           else ""),
            measurement_type="",   # a roster is identity, never a count
            confidence_tier=Tier.B.value,
            entity_match_method=res["match_method"],
            entity_tier=res["entity_tier"],
            source_authority="California Gambling Control Commission",
            source_document_type=f["list_type"], source_url=f["source_url"],
            source_page=f["source_page"], source_quote=f["source_quote"],
            fetched_date=f["fetched_date"], built_date=TODAY,
            built_by_script="code/103_build_california_gaming.py"))
        if f["list_type"] == "cgcc_paying_tribes_list":
            # The last two columns are SDF then RSTF and a tick in one does not
            # imply the other. Which fund is read from WHICH COLUMN the tick
            # sits in, never from how many ticks the row has: 30 of 47 payers
            # pay into only one of the two, and counting glyphs would have
            # silently made every single-tick tribe an SDF payer.
            cols = set((f.get("fund_flag_columns") or "").split(","))
            row["pays_into_sdf"] = "yes" if "sdf" in cols else ""
            row["pays_into_rstf"] = "yes" if "rstf" in cols else ""
        if not res["tribe_id"]:
            review.append(dict(
                review_id="CA-TRIBE:%s" % f["tribe_name_as_published"],
                issue_type="agent_tribe_unresolved:%s" % res["refusal"],
                fund="", name_as_published=f["tribe_name_as_published"],
                context=f["list_type"], evidence=f["facility_name_as_published"],
                question="Which spine entity is this CGCC tribe name?",
                candidate_entities="", source_url=f["source_url"],
                source_page=f["source_page"], source_quote=f["source_quote"][:300],
                YOUR_RULING=""))
        if not fid and fmethod.startswith("unresolved_facility_name"):
            review.append(dict(
                review_id="CA-FACILITY:%s" % f["facility_name_as_published"],
                issue_type="agent_facility_unresolved",
                fund="", name_as_published=f["facility_name_as_published"],
                context="%s / %s" % (f["tribe_name_as_published"], f["casino_city"]),
                evidence="CGCC roster as of %s" % f["as_of_date"],
                question="Which Cedar property is this CGCC casino name, or is "
                         "it genuinely absent from the universe?",
                candidate_entities=fmethod.split(":", 1)[1] if ":" in fmethod else "",
                source_url=f["source_url"], source_page=f["source_page"],
                source_quote=f["source_quote"][:300], YOUR_RULING=""))
        frows.append(row)

    # --- integrity gates --------------------------------------------------
    bad = [r for r in out if not r["source_url"] or not r["source_quote"]]
    assert not bad, "%d rows without source_url or source_quote" % len(bad)
    badf = [r for r in frows if not r["source_url"] or not r["source_quote"]]
    assert not badf, "%d facility rows without provenance" % len(badf)
    badm = [r for r in out
            if r["revenue_evidence_class"] == "EXACT_DERIVED_PROPERTY_REVENUE"
            and r["compact_base_scope"] != "facility"]
    assert not badm, ("%d rows claim property revenue on a non-facility base"
                      % len(badm))

    # --- write ------------------------------------------------------------
    p1 = os.path.join(CLEAN, "ca_gaming_payments.csv")
    with open(p1, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=PAY_FIELDS)
        w.writeheader()
        w.writerows(out)
    # PRESERVE COLUMNS THIS BUILD DOES NOT KNOW ABOUT.
    #
    # AGENTS.md, 2026-09-01: "A rebuild writer on a table other scripts enrich
    # must preserve unknown columns, or the gate's backup diff is the only
    # thing standing between us and silent loss." Measured here the same day:
    # `code/266_apply_gaming_hub_spillover_rulings.py` wrote
    # `entity_tier_basis` and `entity_keyed_date` onto five Barona rows of this
    # file on 2026-08-26 -- each carrying a paragraph of reasoning about why
    # `resolve_entity` refuses that CGCC operator string -- and FAC_FIELDS does
    # not list either column, so this rebuild deleted all of it. `62`'s
    # `files_with_columns_lost_vs_backup` caught it.
    #
    # Carried on `record_id`, which is unique across all 245 rows, and only for
    # columns this build does not itself write, so a fresh value never loses to
    # a stale one.
    p2 = os.path.join(CLEAN, "ca_gaming_facilities_official.csv")
    carried = []
    if os.path.exists(p2):
        with open(p2, encoding="utf-8-sig", newline="") as f:
            prior = list(csv.DictReader(f))
        if prior:
            carried = [c for c in prior[0] if c not in FAC_FIELDS]
            if carried:
                pmap = {r.get("record_id", ""): r for r in prior}
                for r in frows:
                    src = pmap.get(r.get("record_id", ""), {})
                    for c in carried:
                        r.setdefault(c, src.get(c, ""))
                print("  carried %d enricher column(s) forward on record_id: %s"
                      % (len(carried), ", ".join(carried)))
    with open(p2, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FAC_FIELDS + carried)
        w.writeheader()
        w.writerows(frows)
    ded, seenr = [], set()
    for r in review:
        k = (r["review_id"], r["issue_type"])
        if k in seenr:
            continue
        seenr.add(k)
        ded.append(r)
    p3 = os.path.join(REVIEW, "ca_gaming_unresolved_%s.csv" % TODAY)
    with open(p3, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REVIEW_FIELDS)
        w.writeheader()
        w.writerows(ded)
    p4 = os.path.join(INTERIM, "103_zone_log.csv")
    with open(p4, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "zone", "status", "detail"])
        w.writeheader()
        w.writerows(zonelog)

    # --- run summary ------------------------------------------------------
    L = []
    A = L.append
    A("Cedar Press 103 - California gaming (CGCC / CA DOJ)   %s" % TODAY)
    A("=" * 72)
    docs = _manifest_rows()
    A("documents fetched            %d  (%s)"
      % (len(docs), ", ".join("%s=%d" % (k, v) for k, v in
                              Counter(d["doc_class"] for d in docs).most_common())))
    A("payment rows                 %d" % len(out))
    A("facility roster rows         %d" % len(frows))
    A("review rows                  %d" % len(ded))
    A("")
    A("BY FUND x DIRECTION")
    for k, v in sorted(Counter((r["fund"], r["direction"]) for r in out).items()):
        vals = [r for r in out if (r["fund"], r["direction"]) == k]
        per = [r["period_end"] for r in vals if r["period_end"]]
        A("  %-6s %-9s %6d rows  %s .. %s  tribes=%d"
          % (k[0], k[1], v, min(per) if per else "", max(per) if per else "",
             len({r["tribe_id"] for r in vals if r["tribe_id"]})))
    A("")
    A("BY METRIC")
    for k, v in Counter(r["metric"] for r in out).most_common():
        A("  %-52s %6d" % (k, v))
    A("")
    A("ENTITY RESOLUTION")
    for k, v in tr.reasons.most_common():
        A("  %-46s %6d" % (k, v))
    A("  distinct published names        %6d" % len(tr.cache))
    A("  rows with tribe_id              %6d of %d"
      % (sum(1 for r in out if r["tribe_id"]), len(out)))
    A("")
    A("FOOTING (the document's own printed totals)")
    for k, v in Counter(z["status"] for z in zonelog).most_common():
        A("  %-46s %6d" % (k, v))
    A("")
    A("COMPACT INVERTIBILITY (paid_in rows only)")
    pin = [r for r in out if r["direction"] == "paid_in"]
    for k, v in Counter(r["payment_invertible"] for r in pin).most_common():
        A("  invertible=%-16s %6d" % (k or "(unassessed)", v))
    for k, v in Counter(r["revenue_evidence_class"] for r in pin).most_common():
        A("  %-46s %6d" % (k, v))
    for k, v in Counter(r["bound_basis"] for r in pin).most_common():
        A("  bound: %-40s %6d" % (k[:40] or "(none)", v))
    A("  derived tribe-level revenue rows %5d"
      % sum(1 for r in pin if r["derived_tribe_revenue_value"] != ""))
    A("  derived PROPERTY revenue rows    %5d"
      % sum(1 for r in out
            if r["revenue_evidence_class"] == "EXACT_DERIVED_PROPERTY_REVENUE"))
    A("")
    A("SDF LOCAL MITIGATION - extracted, withheld")
    A("  line items parsed from the 2015 JLBC appendices  %d" % n_sdf_withheld)
    A("  published                                             0")
    A("  reason: no tribe is named anywhere in the appendix, and the line "
      "items do not")
    A("          foot against the printed per-county totals in this pass.")
    A("")
    A("EXCLUSIONS (columns, never deletions)")
    for k, v in Counter(r["exclusion_flag"] for r in out).most_common():
        A("  %-46s %6d" % (k or "(none)", v))
    A("")
    A("FACILITY MATCHING")
    for k, v in Counter(r["facility_name_match_method"].split(":")[0]
                        for r in frows).most_common():
        A("  %-46s %6d" % (k, v))
    A("")
    A("INTEGRITY")
    A("  rows missing source_url or source_quote      0 of %d" % len(out))
    A("  rows claiming property revenue on tribe base 0")
    txt = "\n".join(L)
    with open(os.path.join(INTERIM, "103_run_summary.txt"), "w",
              encoding="utf-8") as f:
        f.write(txt + "\n")
    print()
    print(txt)
    return out, frows, ded


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
    if a.stage in ("all", "parse", "build", "resolve", "emit"):
        stage_build()
