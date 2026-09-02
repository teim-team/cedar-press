#!/usr/bin/env python3
"""1082 - TRIBAL DEBT: who lends, who buys the paper, and what the borrower
discloses.

Owns: the REGISTERED-FUND HOLDINGS seam on EDGAR (NPORT-P / NPORT-EX / N-Q /
N-CSR portfolio schedules) and the MUNICIPAL disclosure question (MSRB EMMA),
which this script probes and DECLINES.

Does NOT own: EDGAR transactional forms (8-K/10-K/S-1) - that is
`code/1030_sec_edgar_native_transactions.py`; and the casino MANAGERS' revenue
seam, claimed 2026-09-02 as `code/1080_sec_gaming_facility_revenue.py`. This
script reads 1030's DISCARDED class and touches neither.

THE OWNER'S INFERENCE, WHICH IS THE WHOLE METHOD
------------------------------------------------
    "there's these vulture capital funds that will basically buy bad debt
     from tribes ... If you can invest in these, then they're probably
     available."

Correct, and it generalises: an instrument that can be bought must be
disclosed. A US registered investment company holding a tribal term loan or a
tribal bond must print it in its portfolio schedule with the borrower's name,
the principal balance, the coupon, the maturity and the fair value - and in
NPORT-P, in a machine-readable XML block that also carries `isDefault` and
`areIntrstPmntsInArrs`. That is a mandatory federal disclosure filed BY THE
FUND, so no tribal source's terms of use reach it
(docs/PUBLICATION_POLICY.md, TERMS-SCOPE: "The distinction is authorship, not
subject matter.").

1030's `triage` classed 13,115 of those hits as NOISE - correctly, for its own
question, because a holding is not a transaction. For THIS question the
holding IS the observation.

STAGES
------
  plan      zero network. Builds the fetch queue from 1030's candidate index.
  fetch     one host lock on www.sec.gov, >=0.20s gap, declared UA with
            contact, .part-then-rename, manifest flushed after EVERY request.
  mine      zero network. Parses NPORT `invstOrSec` blocks; stages one row per
            (filing, holding).
  emma      ONE request. Re-probes MSRB EMMA robots.txt and records the
            disposition. It does not fetch EMMA data.
  verify    invariants. Exit 1 on breach.
  selftest  injects a synthetic violation, proves `verify` FIRES on the NAMED
            invariant, restores, proves it passes.

WRITES (all new files; nothing in data/clean is edited)
  data/staging/tribal_debt_holdings.csv          one row per fund-holding
  data/staging/tribal_debt_obligors.csv          one row per obligor
  data/staging/tribal_debt_distress_events.csv   default / arrears observations
  review/1082_fetch_queue.csv
  review/1082_fetch_manifest.csv
  review/1082_unmatched_issuer_names.csv
  review/1082_source_dispositions.csv
  data/raw/external/tribal_debt_1082/*.xml.gz

MONEY FENCE (docs/MONEY_TOTALLING_RULES.md, block TRIBAL-DEBT)
  A principal balance held by ONE fund is that fund's slice of an instrument.
  Summing `principal_usd` across funds does NOT give the instrument's par and
  MUST NOT be added to any deal value or any NIGC revenue figure, nor summed
  across report dates. Every row carries `not_summable_with`.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = "code/1082_tribal_debt_holdings_disclosure.py"
CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
STAGING = CEDAR / "data" / "staging"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
CACHE = CEDAR / "data" / "raw" / "external" / "tribal_debt_1082"

TODAY = datetime.now().strftime("%Y-%m-%d")
UA = "Cedar Press research (elijahsamsonmoreno@gmail.com)"
GAP = 0.20

CANDIDATE_INDEX = REVIEW / "sec_edgar_post2017_candidates_2026-09-01.csv"
QUEUE = REVIEW / "1082_fetch_queue.csv"
MANIFEST = REVIEW / "1082_fetch_manifest.csv"
UNMATCHED = REVIEW / "1082_unmatched_issuer_names.csv"
DISPOSITIONS = REVIEW / "1082_source_dispositions.csv"

HOLDINGS = STAGING / "tribal_debt_holdings.csv"
OBLIGORS = STAGING / "tribal_debt_obligors.csv"
DISTRESS = STAGING / "tribal_debt_distress_events.csv"

csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()


# ------------------------------------------------------------ safe writing --

def merge_header(path, new_keys):
    """RULE 17 / code/845_regenerate_guard.py: DERIVE the header from the LIVE
    file, never a fixed literal. Returns the on-disk header extended with any
    key this run adds, on-disk order first."""
    live = []
    if path.exists():
        with open(path, encoding="utf-8-sig", newline="") as fh:
            r = csv.reader(fh)
            try:
                live = next(r)
            except StopIteration:
                live = []
    seen = set(live)
    return live + [k for k in new_keys if k not in seen]


def write_csv(path, rows, order_hint=()):
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(order_hint)
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    header = merge_header(path, keys)
    tmp = path.with_suffix(path.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    os.replace(tmp, path)
    return header


def read_csv(path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------- host lock --

class HostLock:
    def __init__(self, host, policy, note=""):
        self.host = host
        self.path = LOGS / ("_HOSTLOCK_" + host + ".json")
        self.state = {
            "host": host, "pid": os.getpid(), "script": SCRIPT,
            "claimed_by": "pull",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "active": True, "queue": [], "policy": policy, "note": note,
            "downloaded_this_run": 0, "already_on_disk_skipped": 0,
            "refused_by_host": [], "requests_made": 0,
        }

    def __enter__(self):
        LOGS.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                prev = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                prev = {}
            if prev.get("active") and not prev.get("released"):
                raise SystemExit(
                    "HOSTLOCK HELD on %s by pid %s (%s) since %s. One poller "
                    "per host - deferring, nothing fetched."
                    % (self.host, prev.get("pid"), prev.get("script"),
                       prev.get("claimed_at")))
        self._write()
        return self

    def _write(self):
        self.path.write_text(json.dumps(self.state, indent=1), encoding="utf-8")

    def __exit__(self, *exc):
        self.state["active"] = False
        self.state["released"] = datetime.now(timezone.utc).isoformat()
        self.state["released_by"] = SCRIPT
        self._write()
        return False

    def bump(self, **kw):
        for k, v in kw.items():
            if isinstance(v, int) and isinstance(self.state.get(k), int):
                self.state[k] += v
            else:
                self.state[k] = v
        self._write()


def http_get(url, headers=None, timeout=90):
    h = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return getattr(r, "status", 200), body


# ============================================================== the matcher ==
# A tribal obligor is asserted only on an EXPLICIT tribal-issuer signal in the
# issuer name as the FUND printed it. Nothing here infers a tribe from a
# casino brand: a brand can be licensed to a non-tribal operator.
#
# The negative list is not guesswork either - every entry is a measured
# false-positive class from docs/TRIBAL_DEBT_BUILD_LOG.md, which enumerated
# them against Moody's sitemaps and the EMMA type-ahead.

TRIBAL_SIGNALS = [
    "tribal gaming authority", "tribal gaming", "tribal finance",
    "tribal economic", "tribal development", "tribal utility",
    "tribal council", "tribal enterprise", "tribal authority",
    "indian tribe", "indian nation", "indian community", "indian gaming",
    "indian reservation", "band of ", "pueblo of ", "rancheria",
    "tribe of ", "tribes of ", "nation of indians", "indian housing",
    "native village of", "alaska native", "tribal housing",
    "economic development authority", "gaming authority",
    "gaming corporation", "gaming enterprise", "development authority",
]

# Named tribal obligors that carry no generic signal token in the string a
# fund prints. Each was established as a tribal issuer in
# docs/TRIBAL_DEBT_BUILD_LOG.md (Moody's tribal issuer census, 32 entities)
# or in data/clean/tribal_bond_issuances.csv.
NAMED_OBLIGORS = {
    "mohegan": "Mohegan Tribal Gaming Authority",
    "mashantucket": "Mashantucket (Western) Pequot Tribe",
    "foxwoods": "Mashantucket (Western) Pequot Tribe",
    "seminole hard rock": "Seminole Hard Rock Entertainment",
    "seminole tribe": "Seminole Tribe of Florida",
    "chukchansi": "Chukchansi Economic Development Authority",
    "shingle springs": "Shingle Springs Tribal Gaming Authority",
    "cowlitz": "Cowlitz Tribal Gaming Authority",
    "choctaw resort": "Choctaw Resort Development Enterprise",
    "downstream development": "Downstream Development Authority",
    "snoqualmie entertainment": "Snoqualmie Entertainment Authority",
    "little traverse bay": "Little Traverse Bay Bands of Odawa Indians",
    "river rock": "River Rock Entertainment Authority",
    "tunica-biloxi": "Tunica-Biloxi Gaming Authority",
    "tunica biloxi": "Tunica-Biloxi Gaming Authority",
    "seneca gaming": "Seneca Gaming Corporation",
    "inn of the mountain gods": "Inn of the Mountain Gods Resort and Casino",
    "jamul indian village": "Jamul Indian Village Development Corporation",
    "gun lake": "Gun Lake Tribal Gaming Authority",
    "kalispel": "Kalispel Tribal Economic Authority",
    "pokagon": "Pokagon Gaming Authority",
    "catawba nation gaming": "Catawba Nation Gaming Authority",
    "chumash": "Chumash Casino and Resort Enterprise",
    "cow creek": "Cow Creek Band of Umpqua Tribe of Oregon",
    "warm springs": "Confederated Tribes of Warm Springs",
    "united auburn": "United Auburn Indian Community",
    "lac du flambeau": "Lac du Flambeau Band of Lake Superior Chippewa",
    "lummi": "Lummi Nation",
    "oneida indian nation": "Oneida Indian Nation of New York",
    "salt river pima": "Salt River Pima-Maricopa Indian Community",
    "sault ste marie": "Sault Ste Marie Tribe of Chippewa Indians",
    "white mountain apache": "White Mountain Apache Tribe",
    "yakama": "Yakama Nation",
    "southern ute": "Southern Ute Indian Tribe",
    "navajo nation": "Navajo Nation",
    "navajo tribal utility": "Navajo Tribal Utility Authority",
    "agua caliente": "Agua Caliente Band of Cahuilla Indians",
    "morongo": "Morongo Band of Mission Indians",
    "cabazon": "Cabazon Band of Mission Indians",
    "barona": "Barona Band of Mission Indians",
    "santa rosa rancheria": "Santa Rosa Rancheria Tachi Yokut Tribe",
    "fort mcdowell": "Fort McDowell Yavapai Nation",
    "fort sill apache": "Fort Sill Apache Tribe",
    "grand traverse band": "Grand Traverse Band of Ottawa and Chippewa",
    "laguna development": "Laguna Development Corporation",
    "ak-chin": "Ak-Chin Indian Community",
    "cherokee nation": "Cherokee Nation",
    "eastern band of cherokee": "Eastern Band of Cherokee Indians",
    "chickasaw nation": "Chickasaw Nation",
    "citizen potawatomi": "Citizen Potawatomi Nation",
    "cheyenne river sioux": "Cheyenne River Sioux Tribe",
    "oglala sioux": "Oglala Sioux Tribe",
    "mille lacs": "Mille Lacs Band of Ojibwe",
    "red lake band": "Red Lake Band of Chippewa Indians",
    "san carlos apache": "San Carlos Apache Tribe",
    "standing rock": "Standing Rock Sioux Tribe",
    "three affiliated tribes": "Three Affiliated Tribes of Fort Berthold",
    "tulalip": "Tulalip Tribes",
    "quechan": "Quechan Indian Tribe",
    "quinault": "Quinault Indian Nation",
    "jicarilla": "Jicarilla Apache Nation",
    "blackfeet": "Blackfeet Nation",
    "fort peck": "Fort Peck Assiniboine and Sioux Tribes",
    "prairie band": "Prairie Band Potawatomi Nation",
    "santee sioux": "Santee Sioux Nation",
    "wind creek": "Poarch Band of Creek Indians",
    "poarch": "Poarch Band of Creek Indians",
    "ho-chunk": "Ho-Chunk Nation",
    "san manuel": "San Manuel Band of Mission Indians",
    "yavapai-apache": "Yavapai-Apache Nation",
    "yavapai apache": "Yavapai-Apache Nation",
    "viejas": "Viejas Band of Kumeyaay Indians",
    "sycuan": "Sycuan Band of the Kumeyaay Nation",
    "pechanga": "Pechanga Band of Indians",
    "graton": "Federated Indians of Graton Rancheria",
    "soboba": "Soboba Band of Luiseno Indians",
    "santa ysabel": "Iipay Nation of Santa Ysabel",
    "lake of the torches": "Lac du Flambeau Band of Lake Superior Chippewa",
    "muscogee": "Muscogee (Creek) Nation",
    "osage nation": "Osage Nation",
    "quapaw": "Quapaw Nation",
    "peninsula pacific": None,
}

# Measured false-positive classes. Source: docs/TRIBAL_DEBT_BUILD_LOG.md,
# section "False-positive classes that will keep polluting tribal name
# searches", plus the EMMA type-ahead list in the same document. A hit whose
# name contains one of these is REFUSED, not silently dropped - it is written
# to review/1082_unmatched_issuer_names.csv with the reason.
NEGATIVE = [
    "choctaw generation", "seminole electric", "seminole county",
    "seminole cnty", "saginaw valley state", "shakopee isd",
    "city of shakopee", "muscogee county", "cowlitz county",
    "catawba county", "catawba college", "catawba valley",
    "bristol bay funding", "warm springs rehabilitation",
    "little traverse township", "mohawk industries", "niagara mohawk",
    "dry creek joint elementary", "sovereign debt",
    "indiana ", "indianapolis", "indian hills community college",
    "indian river", "indian trail", "indian prairie", "indian creek",
    "west indian", "east indian", "republic of india", "indian oil",
    "salt river project", "chickasha", "quapaw quarter",
    "lake mohegan fire", "pueblo, colo", "city of pueblo",
    "pueblo county", "pueblo west", "colville, wa", "city of colville",
    "city of sisseton", "town of catawba", "indian head",
    "national finance authority", "united nations",
    "indian ocean", "asian", "indiana university", "indiana state",
    "indiana finance", "indiana municipal", "indiana bond",
]

_ws = re.compile(r"\s+")


def norm(s):
    return _ws.sub(" ", (s or "").strip().lower())


def classify_issuer(name):
    """Returns (verdict, obligor_label, basis). verdict in
    TRIBAL_OBLIGOR / REFUSED_KNOWN_FALSE_POSITIVE / NO_TRIBAL_SIGNAL."""
    n = norm(name)
    if not n:
        return "NO_TRIBAL_SIGNAL", "", "empty issuer name"
    for bad in NEGATIVE:
        if bad in n:
            return ("REFUSED_KNOWN_FALSE_POSITIVE", "",
                    "matched measured false-positive class %r "
                    "(docs/TRIBAL_DEBT_BUILD_LOG.md)" % bad)
    for key, label in NAMED_OBLIGORS.items():
        if label and key in n:
            return ("TRIBAL_OBLIGOR", label,
                    "named tribal obligor token %r; established in "
                    "docs/TRIBAL_DEBT_BUILD_LOG.md or "
                    "data/clean/tribal_bond_issuances.csv" % key)
    for sig in TRIBAL_SIGNALS:
        if sig in n:
            # a bare "development authority" / "gaming authority" with no
            # tribal word anywhere is not evidence of a tribal obligor.
            if sig in ("economic development authority", "development authority",
                       "gaming authority", "gaming corporation",
                       "gaming enterprise"):
                if not any(t in n for t in ("tribal", "tribe", "indian",
                                            "nation", "band", "pueblo",
                                            "rancheria", "native")):
                    continue
            return ("TRIBAL_OBLIGOR", name.strip(),
                    "explicit tribal signal %r in the issuer name as the fund "
                    "printed it" % sig)
    return "NO_TRIBAL_SIGNAL", "", "no tribal signal token"


# =================================================================== plan ====

HOLDINGS_FORMS = {
    "NPORT-P", "NPORT-P/A", "NPORT-EX", "N-Q", "N-Q/A",
    "N-CSR", "N-CSR/A", "N-CSRS", "N-CSRS/A",
    "N-MFP2", "N-MFP2/A", "N-MFP3", "N-MFP3/A", "N-30B-2",
}
# NPORT primary_doc.xml is structured; the rest are HTML/text and are queued
# at lower priority because the mine stage can only read the XML today.
XML_FORMS = {"NPORT-P", "NPORT-P/A", "NPORT-EX"}


def cmd_plan():
    out("=== 1082 plan - build the fetch queue (zero network) ===\n")
    if not CANDIDATE_INDEX.exists():
        raise SystemExit("missing %s" % CANDIDATE_INDEX)
    rows = read_csv(CANDIDATE_INDEX)
    out("  %6d rows in 1030's candidate index" % len(rows))

    by_acc = {}
    for r in rows:
        if r["form"] not in HOLDINGS_FORMS:
            continue
        a = r["accession"]
        e = by_acc.setdefault(a, {
            "accession": a, "cik": r["cik"], "form": r["form"],
            "filer_display_names": r["filer_display_names"],
            "file_date": r["file_date"], "period_ending": r["period_ending"],
            "document_url": r["document_url"],
            "sweep_phrases": set(),
        })
        e["sweep_phrases"].add(r["sweep_phrase"])

    q = []
    for a, e in by_acc.items():
        is_xml = e["form"] in XML_FORMS
        cik = str(int(e["cik"])) if e["cik"].isdigit() else e["cik"]
        accn = a.replace("-", "")
        url = ("https://www.sec.gov/Archives/edgar/data/%s/%s/primary_doc.xml"
               % (cik, accn)) if is_xml else e["document_url"]
        q.append({
            "accession": a, "cik": e["cik"], "form": e["form"],
            "filer_display_names": e["filer_display_names"],
            "file_date": e["file_date"], "period_ending": e["period_ending"],
            "document_url": url,
            "doc_kind": "nport_primary_doc_xml" if is_xml else "html_or_text",
            "priority": "1" if is_xml else "2",
            "sweep_phrases": "; ".join(sorted(e["sweep_phrases"])),
            "queued_by": SCRIPT, "queued_date": TODAY,
            "record_scope": "FETCH_QUEUE_ENTRY_NOT_A_FACT",
        })
    q.sort(key=lambda r: (r["priority"], r["file_date"]))
    write_csv(QUEUE, q)
    from collections import Counter
    out("  %6d distinct accessions queued" % len(q))
    for k, v in Counter(r["form"] for r in q).most_common():
        out("         %-12s %5d" % (k, v))
    out("\n  priority 1 (structured NPORT XML): %d"
        % sum(1 for r in q if r["priority"] == "1"))
    out("  priority 2 (HTML/text schedules) : %d"
        % sum(1 for r in q if r["priority"] == "2"))
    out("\n  wrote %s" % QUEUE)


# ================================================================== fetch ====

def cache_path(accession, kind):
    ext = "xml.gz" if kind == "nport_primary_doc_xml" else "txt.gz"
    return CACHE / ("%s__%s" % (accession, ext))


def cmd_fetch(argv):
    limit = None
    prio = "1"
    for a in argv:
        if a.startswith("--limit="):
            limit = int(a.split("=", 1)[1])
        if a.startswith("--priority="):
            prio = a.split("=", 1)[1]
    q = read_csv(QUEUE)
    if not q:
        raise SystemExit("empty queue - run `plan` first")
    q = [r for r in q if r["priority"] == prio]
    CACHE.mkdir(parents=True, exist_ok=True)

    done = {r["accession"] for r in read_csv(MANIFEST)
            if r.get("http_status") == "200"}
    todo = [r for r in q if r["accession"] not in done]
    if limit:
        todo = todo[:limit]
    out("=== 1082 fetch - priority %s ===" % prio)
    out("  queue %d, already fetched %d, this run %d"
        % (len(q), len(q) - len([r for r in q if r["accession"] not in done]),
           len(todo)))
    if not todo:
        out("  nothing to do")
        return

    man = read_csv(MANIFEST)
    man_keys = {r["accession"] for r in man}
    consecutive_refusals = 0
    deadline = time.time() + 5400

    with HostLock("www.sec.gov",
                  "sequential, single stream, >=%.2fs gap, stop after 5 "
                  "consecutive refusals, 90min deadline" % GAP,
                  "1082 registered-fund holdings schedules") as lock:
        for i, r in enumerate(todo, 1):
            if time.time() > deadline:
                out("  DEADLINE reached, stopping cleanly at %d" % i)
                break
            if consecutive_refusals >= 5:
                out("  5 consecutive refusals, stopping")
                break
            p = cache_path(r["accession"], r["doc_kind"])
            rec = {
                "accession": r["accession"], "cik": r["cik"],
                "form": r["form"], "file_date": r["file_date"],
                "doc_kind": r["doc_kind"],
                "document_url": r["document_url"],
                "local_file": str(p.relative_to(CEDAR)).replace("\\", "/"),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "fetched_by": SCRIPT,
            }
            try:
                status, body = http_get(r["document_url"])
                rec["http_status"] = str(status)
                rec["bytes"] = str(len(body))
                rec["md5"] = hashlib.md5(body).hexdigest()
                tmp = p.with_suffix(p.suffix + ".part")
                with gzip.open(tmp, "wb") as fh:
                    fh.write(body)
                os.replace(tmp, p)
                consecutive_refusals = 0
                lock.bump(downloaded_this_run=1, requests_made=1)
            except urllib.error.HTTPError as e:
                rec["http_status"] = str(e.code)
                rec["note"] = "HTTPError"
                consecutive_refusals += 1
                lock.bump(requests_made=1,
                          refused_by_host=lock.state["refused_by_host"]
                          + ["%s: %s" % (r["accession"], e.code)])
            except Exception as e:
                rec["http_status"] = "ERR"
                rec["note"] = type(e).__name__
                consecutive_refusals += 1
                lock.bump(requests_made=1)
            if r["accession"] in man_keys:
                man = [m for m in man if m["accession"] != r["accession"]]
            man.append(rec)
            man_keys.add(r["accession"])
            write_csv(MANIFEST, man)   # flushed after EVERY request
            if i % 100 == 0:
                out("  %d/%d" % (i, len(todo)))
            time.sleep(GAP)
    out("  done. manifest %s" % MANIFEST)


# =================================================================== mine ====

def _t(el):
    return (el.text or "").strip() if el is not None else ""


def strip_ns(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def mine_nport(path, meta):
    """Yields one dict per tribal holding found in an NPORT primary_doc.xml."""
    with gzip.open(path, "rb") as fh:
        raw = fh.read()
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return [], "xml_parse_error", [], {}
    for el in root.iter():
        el.tag = strip_ns(el.tag)

    gen = root.find(".//genInfo")
    fund_name = _t(gen.find("regName")) if gen is not None else ""
    series_name = _t(gen.find("seriesName")) if gen is not None else ""
    rep_end = _t(gen.find("repPdEnd")) if gen is not None else ""
    rep_date = _t(gen.find("repPdDate")) if gen is not None else ""
    period = rep_date or rep_end or meta.get("period_ending", "")

    hits, seen_names = [], []
    for inv in root.iter("invstOrSec"):
        name = _t(inv.find("name"))
        title = _t(inv.find("title"))
        probe = name if name else title
        verdict, obligor, basis = classify_issuer(probe)
        if verdict != "TRIBAL_OBLIGOR" and title and title != name:
            v2, o2, b2 = classify_issuer(title)
            if v2 == "TRIBAL_OBLIGOR":
                verdict, obligor, basis, probe = v2, o2, b2, title
        if verdict != "TRIBAL_OBLIGOR":
            seen_names.append((probe, verdict, basis))
            continue

        debt = inv.find("debtSec")
        rate = _t(debt.find("annualizedRt")) if debt is not None else ""
        mat = _t(debt.find("maturityDt")) if debt is not None else ""
        isdef = _t(debt.find("isDefault")) if debt is not None else ""
        arrears = (_t(debt.find("areIntrstPmntsInArrs"))
                   if debt is not None else "")
        paidkind = _t(debt.find("isPaidKind")) if debt is not None else ""

        hits.append({
            "holding_id": "",
            "obligor_name_as_published": probe,
            "obligor_label": obligor,
            "obligor_match_basis": basis,
            "security_title_as_published": title,
            "cusip": _t(inv.find("cusip")),
            "isin": _t(inv.find(".//isin")),
            "lei": _t(inv.find("lei")),
            "balance_units": _t(inv.find("balance")),
            "units_kind": _t(inv.find("units")),
            "principal_usd": (_t(inv.find("balance"))
                              if _t(inv.find("units")) == "PA" else ""),
            "fair_value_usd": _t(inv.find("valUSD")),
            "pct_of_fund_net_assets": _t(inv.find("pctVal")),
            "currency": _t(inv.find("curCd")),
            "coupon_annualized_pct": rate,
            "maturity_date": mat,
            "is_default_as_filed": isdef,
            "interest_payments_in_arrears_as_filed": arrears,
            "payment_in_kind_as_filed": paidkind,
            "asset_category": _t(inv.find("assetCat")),
            "issuer_category": _t(inv.find("issuerCat")),
            "investment_country": _t(inv.find("invCountry")),
            "is_restricted_security": _t(inv.find("isRestrictedSec")),
            "fair_value_level": _t(inv.find("fairValLevel")),
            "holder_fund_registrant": fund_name,
            "holder_fund_series": series_name,
            "holder_cik": meta.get("cik", ""),
            "holder_filer_display": meta.get("filer_display_names", ""),
            "report_period_end": period,
            "filing_form": meta.get("form", ""),
            "filing_date": meta.get("file_date", ""),
            "accession": meta.get("accession", ""),
        })
    return hits, "ok", seen_names, {"fund": fund_name, "period": period}


def load_spine():
    reg = read_csv(SPINE / "cedar_identity_register.csv")
    idx = []
    for r in reg:
        cn = norm(r.get("canonical_name", ""))
        fr = norm(r.get("federal_register_legal_name", ""))
        if cn:
            idx.append((cn, r))
        if fr and fr != cn:
            idx.append((fr, r))
    idx.sort(key=lambda x: -len(x[0]))
    return idx


def resolve_obligor(label, spine_idx):
    """Conservative. Returns (cedar_uid, handle, method, tier).
    Tier is INHERITED from the strength of the evidence, never from the
    exactness of the key - START_HERE trap 1."""
    n = norm(label)
    if not n:
        return "", "", "", ""
    for cname, r in spine_idx:
        if len(cname) < 5:
            continue
        if cname == n:
            return (r["cedar_uid"], r["handle"], "exact_canonical_name", "A")
    for cname, r in spine_idx:
        if len(cname) < 6:
            continue
        if re.search(r"\b" + re.escape(cname) + r"\b", n):
            return (r["cedar_uid"], r["handle"],
                    "spine_name_is_a_whole_token_run_inside_obligor_name", "B")
    return "", "", "no_spine_match", ""


NOT_SUMMABLE = (
    "a principal balance held by ONE fund is that fund's slice of an "
    "instrument, not the instrument's par. NEVER sum principal_usd or "
    "fair_value_usd across funds, across report periods, or against "
    "deals_classified.Announced_Value_USD, tribal_bond_issuances.par_amount, "
    "nigc_regional_ggr, or gaming_revenue_bounds."
)


def cmd_mine():
    out("=== 1082 mine - parse the cached holdings schedules (zero network) ===\n")
    man = {r["accession"]: r for r in read_csv(MANIFEST)
           if r.get("http_status") == "200"}
    out("  %d fetched documents in the manifest" % len(man))
    spine_idx = load_spine()
    out("  %d spine name keys" % len(spine_idx))

    rows, unmatched, parse_fail, docs_read = [], {}, 0, 0
    for accn, m in man.items():
        p = CEDAR / m["local_file"]
        if not p.exists():
            continue
        if m.get("doc_kind") != "nport_primary_doc_xml":
            continue
        docs_read += 1
        hits, status, seen, _ = mine_nport(p, m)
        if status != "ok":
            parse_fail += 1
            continue
        for name, verdict, basis in seen:
            if not name:
                continue
            k = (name, verdict)
            u = unmatched.setdefault(k, {
                "issuer_name_as_published": name, "verdict": verdict,
                "basis": basis, "observations": 0,
                "example_accession": accn,
                "found_by": SCRIPT, "found_date": TODAY,
                "record_scope": "REFUSED_OR_UNMATCHED_NOT_A_FACT",
            })
            u["observations"] += 1
        rows.extend(hits)

    out("  %d NPORT XML documents read, %d parse failures" % (docs_read, parse_fail))
    out("  %d tribal holdings observed" % len(rows))

    seq = 0
    obligor_agg = {}
    distress = []
    for r in rows:
        seq += 1
        r["holding_id"] = "TDH-%06d" % seq
        cu, hd, meth, tier = resolve_obligor(r["obligor_label"], spine_idx)
        r["obligor_cedar_uid"] = cu
        r["obligor_cedar_handle"] = hd
        r["obligor_entity_match_method"] = meth
        r["obligor_entity_tier"] = tier
        r["assertion_class"] = "REGISTERED_FUND_PORTFOLIO_SCHEDULE"
        r["evidence_class"] = (
            "mandatory SEC portfolio disclosure filed BY THE FUND under the "
            "Investment Company Act; a third party's filing about the "
            "obligor, not the obligor's own publication")
        r["source_authority"] = "U.S. Securities and Exchange Commission, EDGAR"
        r["source_document_type"] = "form_nport_p_primary_doc_xml"
        r["source_url"] = (
            "https://www.sec.gov/Archives/edgar/data/%s/%s/primary_doc.xml"
            % (str(int(r["holder_cik"])) if str(r["holder_cik"]).isdigit()
               else r["holder_cik"], r["accession"].replace("-", "")))
        r["measurement_type"] = "one fund's position in one instrument, as of report_period_end"
        r["not_summable_with"] = NOT_SUMMABLE
        r["confidence_tier"] = "A" if r["cusip"] else "B"
        r["confidence_tier_basis"] = (
            "A: the fund printed a CUSIP, so the instrument is identified. "
            "B: no CUSIP in the filing; the instrument is named but not keyed. "
            "This is the tier of the INSTRUMENT identification, NOT of the "
            "entity link - obligor_entity_tier carries that separately.")
        r["built_by_script"] = SCRIPT
        r["built_date"] = TODAY
        r["record_scope"] = "FUND_HOLDING_OBSERVATION"

        key = r["obligor_label"]
        o = obligor_agg.setdefault(key, {
            "obligor_label": key,
            "obligor_cedar_uid": cu, "obligor_cedar_handle": hd,
            "obligor_entity_match_method": meth,
            "obligor_entity_tier": tier,
            "names_as_published": set(), "cusips": set(),
            "holder_funds": set(), "observations": 0,
            "first_report_period": r["report_period_end"],
            "last_report_period": r["report_period_end"],
            "max_single_fund_principal_usd": 0.0,
            "any_default_flag": "no", "any_arrears_flag": "no",
        })
        o["names_as_published"].add(r["obligor_name_as_published"])
        if r["cusip"]:
            o["cusips"].add(r["cusip"])
        o["holder_funds"].add(r["holder_fund_registrant"] or
                              r["holder_filer_display"])
        o["observations"] += 1
        if r["report_period_end"]:
            if not o["first_report_period"] or r["report_period_end"] < o["first_report_period"]:
                o["first_report_period"] = r["report_period_end"]
            if r["report_period_end"] > o["last_report_period"]:
                o["last_report_period"] = r["report_period_end"]
        try:
            v = float(r["principal_usd"] or 0)
            o["max_single_fund_principal_usd"] = max(
                o["max_single_fund_principal_usd"], v)
        except ValueError:
            pass
        if (r["is_default_as_filed"] or "").lower() == "y":
            o["any_default_flag"] = "yes"
        if (r["interest_payments_in_arrears_as_filed"] or "").lower() == "y":
            o["any_arrears_flag"] = "yes"
        if ((r["is_default_as_filed"] or "").lower() == "y"
                or (r["interest_payments_in_arrears_as_filed"] or "").lower() == "y"):
            distress.append({
                "distress_id": "TDD-%06d" % (len(distress) + 1),
                "obligor_label": key,
                "obligor_cedar_uid": cu,
                "obligor_name_as_published": r["obligor_name_as_published"],
                "security_title_as_published": r["security_title_as_published"],
                "cusip": r["cusip"],
                "observed_as_of": r["report_period_end"],
                "is_default_as_filed": r["is_default_as_filed"],
                "interest_payments_in_arrears_as_filed":
                    r["interest_payments_in_arrears_as_filed"],
                "principal_usd": r["principal_usd"],
                "fair_value_usd": r["fair_value_usd"],
                "holder_fund_registrant": r["holder_fund_registrant"],
                "accession": r["accession"],
                "source_url": r["source_url"],
                "sovereign_immunity_caution": (
                    "A tribal obligor is a sovereign. `isDefault` here is the "
                    "FUND's characterisation of the security under Item C.9 of "
                    "Form N-PORT; it is not a court finding, not a corporate "
                    "insolvency, and says nothing about any waiver of "
                    "sovereign immunity or the recourse available. Quote the "
                    "instrument, not this flag."),
                "assertion_class": "REGISTERED_FUND_PORTFOLIO_SCHEDULE",
                "built_by_script": SCRIPT, "built_date": TODAY,
                "record_scope": "DISTRESS_FLAG_AS_FILED_BY_A_THIRD_PARTY",
            })

    obligors = []
    for k, o in sorted(obligor_agg.items()):
        o["names_as_published"] = " | ".join(sorted(o["names_as_published"]))
        o["cusips"] = " | ".join(sorted(o["cusips"]))
        o["n_holder_funds"] = len(o["holder_funds"])
        o["holder_funds"] = " | ".join(sorted(x for x in o["holder_funds"] if x))
        o["max_single_fund_principal_usd"] = (
            "%.2f" % o["max_single_fund_principal_usd"]
            if o["max_single_fund_principal_usd"] else "")
        o["not_summable_with"] = NOT_SUMMABLE
        o["built_by_script"] = SCRIPT
        o["built_date"] = TODAY
        o["record_scope"] = "OBLIGOR_ROLLUP_OF_FUND_OBSERVATIONS"
        obligors.append(o)

    write_csv(HOLDINGS, rows, ["holding_id", "obligor_label",
                               "obligor_cedar_uid", "obligor_name_as_published"])
    write_csv(OBLIGORS, obligors, ["obligor_label", "obligor_cedar_uid"])
    write_csv(DISTRESS, distress, ["distress_id", "obligor_label"])
    write_csv(UNMATCHED, sorted(unmatched.values(),
                                key=lambda r: -r["observations"]))

    out("\n  holdings      %5d -> %s" % (len(rows), HOLDINGS))
    out("  obligors      %5d -> %s" % (len(obligors), OBLIGORS))
    out("  distress      %5d -> %s" % (len(distress), DISTRESS))
    out("  unmatched/refused issuer names %5d -> %s"
        % (len(unmatched), UNMATCHED))
    linked = sum(1 for o in obligors if o["obligor_cedar_uid"])
    out("\n  obligors resolved to a Cedar entity: %d of %d"
        % (linked, len(obligors)))


# =================================================================== emma ====

def cmd_emma():
    """ONE request. Re-probe the MSRB EMMA robots surface and record the
    disposition. This does NOT fetch EMMA data - the refusal recorded as
    SK-TD-001 in docs/TRIBAL_DEBT_BUILD_LOG.md stands, and it is a COMMERCIAL
    blocker for a paid product, not merely an access note."""
    out("=== 1082 emma - re-probe the disposition, fetch nothing ===\n")
    disp = []
    with HostLock("emma.msrb.org", "single request, robots only",
                  "1082 EMMA disposition re-probe") as lock:
        try:
            status, body = http_get("https://emma.msrb.org/robots.txt")
            lock.bump(requests_made=1, downloaded_this_run=1)
            txt = body.decode("utf-8", "replace").replace("\x00", "")
            out("  robots.txt HTTP %s:" % status)
            for line in txt.splitlines():
                if line.strip():
                    out("    %s" % line.strip())
            robots = " / ".join(l.strip() for l in txt.splitlines() if l.strip())
        except Exception as e:
            robots = "probe failed: %s" % type(e).__name__
            out("  " + robots)
            lock.bump(requests_made=1)

    disp.append({
        "source": "MSRB EMMA (emma.msrb.org) continuing-disclosure documents",
        "what_it_would_give": (
            "annual audited financial statements and operating data for tribal "
            "government and tribal gaming-authority obligors, plus material "
            "event notices (default, forbearance, rating change). For a gaming "
            "authority obligor the audited statements routinely carry "
            "facility-level gaming revenue - the figure NIGC does not publish."),
        "disposition": "CONSTRAINED",
        "disposition_basis": (
            "MSRB Terms of Use prohibit \"any data mining, crawling, "
            "'scraping', robot or similar automated or data gathering or "
            "extraction method\" AND prohibit using the content \"to develop "
            "or create a database to be sold, leased, furnished, licensed or "
            "otherwise exploited.\" Cedar Press is a paid product, so the "
            "second clause bites even on a hand-collected figure. Recorded as "
            "SK-TD-001 in docs/TRIBAL_DEBT_BUILD_LOG.md 2026-08-05 and "
            "re-affirmed here."),
        "robots_txt_as_measured": robots,
        "robots_is_not_the_blocker": (
            "robots.txt disallows only /*.pdf$. The binding constraint is the "
            "Terms of Use, not robots - do not read a permissive robots line "
            "as permission."),
        "the_clean_routes_back_in": (
            "(a) an MSRB data licence - MSRB sells subscription feeds; "
            "(b) sourcing the same official statements and continuing "
            "disclosures from the ISSUERS and UNDERWRITERS directly, which is "
            "a different author and therefore a different terms answer "
            "(docs/PUBLICATION_POLICY.md, TERMS-SCOPE)."),
        "owner_decision_required": "yes",
        "probed_by": SCRIPT, "probed_date": TODAY,
        "record_scope": "SOURCE_DISPOSITION_NOT_A_FACT_ABOUT_AN_ENTITY",
    })
    disp.append({
        "source": "SEC EDGAR registered-fund portfolio schedules (NPORT-P etc.)",
        "what_it_would_give": (
            "borrower, principal balance, coupon, maturity, fair value and "
            "as-filed default/arrears flags for any tribal instrument a US "
            "registered fund holds."),
        "disposition": "ACQUIRED_BY_THIS_SCRIPT",
        "disposition_basis": (
            "Mandatory federal disclosure filed by the FUND. No tribal "
            "source's terms reach it; the eight hard-listed sources are "
            "unaffected because the author is a third party "
            "(docs/PUBLICATION_POLICY.md, TERMS-SCOPE)."),
        "robots_txt_as_measured": "sec.gov permits automated access at <=10 req/s with a declared User-Agent",
        "robots_is_not_the_blocker": "",
        "the_clean_routes_back_in": "",
        "owner_decision_required": "no",
        "probed_by": SCRIPT, "probed_date": TODAY,
        "record_scope": "SOURCE_DISPOSITION_NOT_A_FACT_ABOUT_AN_ENTITY",
    })
    write_csv(DISPOSITIONS, disp)
    out("\n  wrote %s" % DISPOSITIONS)


# ================================================================= verify ====

INVARIANTS = [
    "I1_every_holding_names_an_obligor",
    "I2_every_holding_carries_a_source_url",
    "I3_no_holding_asserts_a_summable_total",
    "I4_no_refused_false_positive_reached_the_holdings_table",
    "I5_entity_tier_is_blank_when_there_is_no_entity_link",
    "I6_every_distress_row_is_backed_by_an_as_filed_flag",
    "I7_no_fabricated_money_every_amount_is_blank_or_numeric",
]


def cmd_verify():
    out("=== 1082 verify ===\n")
    breaches = []
    rows = read_csv(HOLDINGS)
    dist = read_csv(DISTRESS)
    out("  holdings %d, distress %d" % (len(rows), len(dist)))
    if not rows:
        out("  NOTHING TO VERIFY - run mine first")
        return 0

    n = sum(1 for r in rows if not r.get("obligor_label", "").strip())
    if n:
        breaches.append(("I1_every_holding_names_an_obligor",
                         "%d holdings with a blank obligor_label" % n))

    n = sum(1 for r in rows if not r.get("source_url", "").startswith("https://"))
    if n:
        breaches.append(("I2_every_holding_carries_a_source_url",
                         "%d holdings with no https source_url" % n))

    n = sum(1 for r in rows if not r.get("not_summable_with", "").strip())
    if n:
        breaches.append(("I3_no_holding_asserts_a_summable_total",
                         "%d holdings with an empty not_summable_with" % n))

    bad = []
    for r in rows:
        nm = norm(r.get("obligor_name_as_published", ""))
        for b in NEGATIVE:
            if b in nm:
                bad.append((r.get("holding_id"), b))
                break
    if bad:
        breaches.append(
            ("I4_no_refused_false_positive_reached_the_holdings_table",
             "%d holdings match a measured false-positive class, e.g. %s"
             % (len(bad), bad[:3])))

    n = sum(1 for r in rows
            if r.get("obligor_entity_tier", "").strip()
            and not r.get("obligor_cedar_uid", "").strip())
    if n:
        breaches.append(("I5_entity_tier_is_blank_when_there_is_no_entity_link",
                         "%d holdings carry a tier with no cedar_uid - the "
                         "START_HERE trap-1 shape" % n))

    n = 0
    for r in dist:
        f1 = (r.get("is_default_as_filed") or "").lower()
        f2 = (r.get("interest_payments_in_arrears_as_filed") or "").lower()
        if f1 != "y" and f2 != "y":
            n += 1
    if n:
        breaches.append(("I6_every_distress_row_is_backed_by_an_as_filed_flag",
                         "%d distress rows with neither flag set to Y" % n))

    n = 0
    for r in rows:
        for c in ("principal_usd", "fair_value_usd", "coupon_annualized_pct",
                  "pct_of_fund_net_assets"):
            v = (r.get(c) or "").strip()
            if v:
                try:
                    float(v)
                except ValueError:
                    n += 1
    if n:
        breaches.append(("I7_no_fabricated_money_every_amount_is_blank_or_numeric",
                         "%d non-numeric money/rate cells" % n))

    for name in INVARIANTS:
        hit = [b for b in breaches if b[0] == name]
        out("  %-58s %s" % (name, "BREACH" if hit else "ok"))
        for _, msg in hit:
            out("      %s" % msg)
    if breaches:
        out("\n  VERIFY FAILED - %d invariant(s) breached" % len(breaches))
        return 1
    out("\n  VERIFY PASSED")
    return 0


def cmd_selftest():
    """A check does not count until a fixture proves it FIRES.
    docs/AGENT_FIELD_GUIDE.md section 3."""
    out("=== 1082 selftest - prove verify FIRES on a synthetic violation ===\n")
    if not HOLDINGS.exists():
        raise SystemExit("run mine first - selftest needs a live table")
    backup = HOLDINGS.read_bytes()
    try:
        rc = cmd_verify()
        if rc != 0:
            out("\n  ABORT: the live table is already RED; fix it before "
                "selftesting.")
            return 1
        out("\n  baseline GREEN. Now injecting violations, one at a time.\n")

        rows = read_csv(HOLDINGS)
        cases = [
            ("I1_every_holding_names_an_obligor",
             lambda r: r.update({"obligor_label": ""})),
            ("I2_every_holding_carries_a_source_url",
             lambda r: r.update({"source_url": "not-a-url"})),
            ("I3_no_holding_asserts_a_summable_total",
             lambda r: r.update({"not_summable_with": ""})),
            ("I4_no_refused_false_positive_reached_the_holdings_table",
             lambda r: r.update(
                 {"obligor_name_as_published": "Seminole Electric Cooperative"})),
            ("I5_entity_tier_is_blank_when_there_is_no_entity_link",
             lambda r: r.update({"obligor_cedar_uid": "",
                                 "obligor_entity_tier": "A"})),
            ("I7_no_fabricated_money_every_amount_is_blank_or_numeric",
             lambda r: r.update({"principal_usd": "about $10 million"})),
        ]
        failures = []
        for name, mutate in cases:
            r2 = [dict(x) for x in rows]
            mutate(r2[0])
            write_csv(HOLDINGS, r2)
            import io as _io
            import contextlib
            buf = _io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cmd_verify()
            txt = buf.getvalue()
            fired_named = ("%-58s BREACH" % name) in txt or (
                name in txt and "BREACH" in txt.split(name, 1)[1][:12])
            ok = (rc == 1) and fired_named
            out("  %-58s %s" % (name, "FIRES" if ok else "DID NOT FIRE"))
            if not ok:
                failures.append(name)

        # I6 lives in the distress table
        dbak = DISTRESS.read_bytes() if DISTRESS.exists() else None
        drows = read_csv(DISTRESS)
        name = "I6_every_distress_row_is_backed_by_an_as_filed_flag"
        if drows:
            d2 = [dict(x) for x in drows]
            d2[0]["is_default_as_filed"] = "N"
            d2[0]["interest_payments_in_arrears_as_filed"] = "N"
            write_csv(DISTRESS, d2)
        else:
            write_csv(DISTRESS, [{
                "distress_id": "TDD-SELFTEST", "obligor_label": "SYNTHETIC",
                "is_default_as_filed": "N",
                "interest_payments_in_arrears_as_filed": "N"}])
        import io as _io
        import contextlib
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cmd_verify()
        txt = buf.getvalue()
        ok = rc == 1 and name in txt and "BREACH" in txt.split(name, 1)[1][:12]
        out("  %-58s %s" % (name, "FIRES" if ok else "DID NOT FIRE"))
        if not ok:
            failures.append(name)
        if dbak is not None:
            DISTRESS.write_bytes(dbak)
        elif DISTRESS.exists():
            DISTRESS.unlink()

        HOLDINGS.write_bytes(backup)
        rc = cmd_verify()
        out("\n  restored; verify now returns %d (expected 0)" % rc)
        if failures or rc != 0:
            out("  SELFTEST FAILED: %s" % (failures or "restore did not clear"))
            return 1
        out("  SELFTEST PASSED - every invariant fires on its own violation "
            "and the table is restored byte-for-byte.")
        return 0
    finally:
        if HOLDINGS.read_bytes() != backup:
            HOLDINGS.write_bytes(backup)


# =================================================================== main ====

USAGE = """usage: py -3 code/1082_tribal_debt_holdings_disclosure.py <stage>

  plan        build the fetch queue from 1030's candidate index (no network)
  fetch       fetch the queue  [--priority=1|2] [--limit=N]
  mine        parse the cache and stage the tables (no network)
  emma        re-probe and record the MSRB EMMA disposition (1 request)
  verify      invariants; exit 1 on breach
  selftest    prove verify fires on a synthetic violation
"""


def main(argv):
    if not argv:
        out(USAGE)
        return 0
    c = argv[0]
    if c == "plan":
        cmd_plan()
    elif c == "fetch":
        cmd_fetch(argv[1:])
    elif c == "mine":
        cmd_mine()
    elif c == "emma":
        cmd_emma()
    elif c == "verify":
        return cmd_verify()
    elif c == "selftest":
        return cmd_selftest()
    else:
        out(USAGE)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
