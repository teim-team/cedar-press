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
    # ADDED 2026-09-02 after auditing review/1082_unmatched_issuer_names.csv
    # against the Moody's tribal issuer census and the EMMA roster in
    # docs/TRIBAL_DEBT_BUILD_LOG.md. Of 10,694 unmatched issuer names, exactly
    # ONE was a real tribal obligor the matcher had missed - an initialism with
    # no tribal word in it. Cedar already resolves PCI as Poarch Creek Indians
    # (logs/_HOSTLOCK_www.pci-nsn.gov.json, and the tribe's own domain is
    # pci-nsn.gov). 51 observations.
    "pci gaming": "PCI Gaming Authority (Poarch Band of Creek Indians)",
    # Funds abbreviate to fit a fixed-width field. These renderings were
    # observed verbatim in the cached NPORT XML, not invented.
    "sthrn ute": "Southern Ute Indian Tribe",
    "mashantucket w": "Mashantucket (Western) Pequot Tribe",
    "peninsula pacific": None,
}

# The distinctive token that identified an obligor is also the best key for
# finding that obligor in the spine, because the spine's canonical names are
# short ("Quapaw", "Southern Ute") while a fund prints the full legal issuer.
def obligor_keys_for(label):
    """EVERY key that maps to this label, longest first. Returning only the
    longest was a bug: the abbreviation key 'mashantucket w' outranked
    'mashantucket' and then failed to match the spine's 'Mashantucket
    Pequot'."""
    n = norm(label)
    keys = [k for k, lab in NAMED_OBLIGORS.items()
            if lab and (lab == label or k in n)]
    return sorted(set(keys), key=len, reverse=True)


# A tribal ENTERPRISE is not its NATION, and no string match will bridge the
# two: "Downstream Development Authority" shares no token with "Quapaw".
# These are stated relationships, each with the source that states it, NOT
# inferences. The link is to the NATION; the obligor stays named as filed.
ENTERPRISE_OF = {
    "Downstream Development Authority": (
        "Quapaw Nation",
        "the fund itself prints the full legal name \"Downstream Development "
        "Authority of the Quapaw Tribe of Oklahoma\" - the relationship is in "
        "the disclosure, not inferred"),
    "Inn of the Mountain Gods Resort and Casino": (
        "Mescalero Apache",
        "chartered enterprise of the Mescalero Apache Tribe; recorded as a "
        "tribal rated entity in the Moody's tribal issuer census, "
        "docs/TRIBAL_DEBT_BUILD_LOG.md"),
    "PCI Gaming Authority (Poarch Band of Creek Indians)": (
        "Poarch",
        "PCI = Poarch Creek Indians; the nation's own domain is pci-nsn.gov, "
        "already recorded in Cedar (logs/_HOSTLOCK_www.pci-nsn.gov.json)"),
    "Mohegan Tribal Gaming Authority": (
        "Mohegan",
        "instrumentality of the Mohegan Tribe of Indians of Connecticut, "
        "named as such in its own SEC filings"),
    "Chukchansi Economic Development Authority": (
        "Picayune",
        "economic development authority of the Picayune Rancheria of the "
        "Chukchansi Indians; Cedar's spine holds that nation as 'Picayune'"),
    "River Rock Entertainment Authority": (
        "Dry Creek",
        "instrumentality of the Dry Creek Rancheria Band of Pomo Indians; "
        "EMMA lists the issuer as 'River Rock Entertainment Auth / Dry Creek "
        "Rancheria CA' (docs/TRIBAL_DEBT_BUILD_LOG.md)"),
    "Snoqualmie Entertainment Authority": (
        "Snoqualmie", "instrumentality of the Snoqualmie Indian Tribe"),
    "Shingle Springs Tribal Gaming Authority": (
        "Shingle Springs",
        "instrumentality of the Shingle Springs Band of Miwok Indians"),
    "Cowlitz Tribal Gaming Authority": (
        "Cowlitz", "instrumentality of the Cowlitz Indian Tribe"),
    "Gun Lake Tribal Gaming Authority": (
        "Match-e-be-nash-she-wish Band",
        "instrumentality of the Match-e-be-nash-she-wish Band of Pottawatomi "
        "Indians, known as the Gun Lake Tribe; Cedar's spine holds the "
        "federally recognized name"),
    "Kalispel Tribal Economic Authority": (
        "Kalispel", "instrumentality of the Kalispel Tribe of Indians"),
    "Jamul Indian Village Development Corporation": (
        "Jamul", "development corporation of the Jamul Indian Village"),
    "Tunica-Biloxi Gaming Authority": (
        "Tunica-Biloxi",
        "instrumentality of the Tunica-Biloxi Tribe of Louisiana"),
    "Choctaw Resort Development Enterprise": (
        "Mississippi Choctaw",
        "enterprise of the Mississippi Band of Choctaw Indians"),
    "Mashantucket (Western) Pequot Tribe": (
        "Mashantucket Pequot",
        "the same nation; Cedar's spine records the canonical name without "
        "the statutory parenthetical"),
    "Little Traverse Bay Bands of Odawa Indians": (
        "Little Traverse", "the same nation, spine short name"),
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
# MEASURED 2026-09-02, not assumed: only NPORT-P carries `primary_doc.xml`.
# NPORT-EX ships an HTML exhibit instead (accession 0001752724-19-046565 ->
# QTLY_2638_20190331.htm, index.json confirms no XML in the folder), so
# constructing primary_doc.xml for it returns 404 every time.
XML_FORMS = {"NPORT-P", "NPORT-P/A"}


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
                # STANDING RULE (START_HERE): only 404 and 403 are facts about
                # an object. A 404 means this accession has no document at
                # this path - it must NOT trip the refusal circuit breaker,
                # which exists to detect the HOST turning us away.
                if e.code in (404, 403):
                    rec["note"] = "HTTP %d - fact about the object, not a refusal" % e.code
                    consecutive_refusals = 0
                else:
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
    # Third pass: the distinctive obligor token against the spine. This is a
    # CONTAINMENT match and AGENTS.md forbids containment from keying a
    # dollar. It does not key one here: the money on these rows is the FUND's
    # position and is attributed to the fund, not to the tribe. The entity
    # link is descriptive, and tier B never publishes alone.
    for key in obligor_keys_for(label):
        if len(key) < 6:
            continue
        for cname, r in spine_idx:
            if len(cname) < 5:
                continue
            if key in cname or cname in key:
                return (r["cedar_uid"], r["handle"],
                        "named_obligor_token_%r_matches_spine_name_%r_"
                        "CONTAINMENT_descriptive_only_never_keys_a_dollar"
                        % (key, cname), "B")
    # Fourth pass: a STATED enterprise-to-nation relationship, each carrying
    # the source that states it. Never an inference from a name - no string
    # match can bridge "Downstream Development Authority" and "Quapaw".
    if label in ENTERPRISE_OF:
        nation, basis = ENTERPRISE_OF[label]
        nn = norm(nation)
        for cname, r in spine_idx:
            if cname == nn:
                return (r["cedar_uid"], r["handle"],
                        "stated_enterprise_of_nation: %s" % basis, "B")
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


# ================================================================ revenue ====
# A tribal gaming authority that sold 144A notes with registration rights ends
# up an SEC REPORTING COMPANY - and then files AUDITED financial statements
# whose MD&A discusses each property by name. That is facility-level revenue
# for an operation NIGC will only report inside a regional aggregate, and it
# exists BECAUSE OF THE DEBT. It is squarely this workstream's material.
#
# Taken here rather than left for `code/1080_sec_gaming_facility_revenue.py`
# (public casino MANAGERS' filings), on the coordinator's instruction: these
# are the OBLIGOR's own filings, not a manager's, and 1080 is an unimplemented
# placeholder whose agent was killed.
#
# WHAT THIS IS NOT: "net revenues" is TOTAL property revenue and INCLUDES
# non-gaming (hotel, food, entertainment, retail). It is NOT gaming revenue and
# NOT comparable to NIGC gross gaming revenue, which is gaming win only. Every
# row says so in `measurement_type`.

REVENUE_SOURCE_MANIFEST = REVIEW / "sec_edgar_1030_fetch_manifest.csv"
REVENUE_OUT = STAGING / "tribal_obligor_property_revenue.csv"

REVENUE_CIKS = {
    "1005276": ("Mohegan Tribal Gaming Authority", "Mohegan", "CE-0016X-GY"),
    "1296785": ("Seneca Gaming Corporation", "Seneca", "CE-001AC-YN"),
    "1296784": ("Seneca Niagara Falls Gaming Corp", "Seneca", "CE-001AC-YN"),
    "1296786": ("Seneca Erie Gaming Corp", "Seneca", "CE-001AC-YN"),
    "1296783": ("Seneca Territory Gaming Corp", "Seneca", "CE-001AC-YN"),
    "1141344": ("Choctaw Resort Development Enterprise",
                "Mississippi Choctaw", ""),
    "1430349": ("Cheyenne River Sioux Tribal Finance Corp",
                "Cheyenne River Sioux Tribe", ""),
}

# Property heading -> Cedar facility_id, verified against
# data/clean/gaming_facilities.csv on 2026-09-02. A blank id is NOT a failed
# match; the reason is recorded in the value.
REVENUE_PROPERTIES = {
    "Mohegan Sun": ("CCP-45100", "Mohegan Sun", "CT"),
    "Mohegan Sun Pocono": ("VP-0034", "Mohegan Pennsylvania", "PA"),
    "Seneca Niagara Falls Casino": ("CCP-565900",
                                    "Seneca Niagara Casino & Hotel", "NY"),
    "Seneca Niagara": ("CCP-565900", "Seneca Niagara Casino & Hotel", "NY"),
    "Seneca Allegany": ("CCP-635600", "Seneca Allegany Casino & Hotel", "NY"),
    "Seneca Buffalo Creek": ("CCP-824100", "Seneca Buffalo Creek Casino", "NY"),
    "MGE Niagara Resorts": ("", "OUT_OF_UNIVERSE_Ontario_Canada", ""),
    "Niagara Resorts": ("", "OUT_OF_UNIVERSE_Ontario_Canada", ""),
    "Inspire Entertainment Resort": ("", "OUT_OF_UNIVERSE_Incheon_Korea", ""),
}

# The sentence must carry a DIRECTION VERB and then "to $X" - that is what
# makes the dollar the RESULTING figure. Without the verb the first draft
# matched "the acquisition of the MGE Niagara Resorts, which contributed
# $112.5 million TO net revenues" and would have booked a CONTRIBUTION as a
# property total. The verb is the whole guard. Do not relax it.
REV_PAT = re.compile(
    r"Net revenues\s+(increased|declined|decreased|grew|rose|fell)\b"
    r"[^|]{0,170}?\bto\s*\$\s?([\d,]+(?:\.\d+)?)\s*(million|billion)\s+"
    r"for the (?:fiscal )?year ended\s+([A-Z][a-z]+\s*\d{1,2},?\s*\d{4})",
    re.I)


def _flatten(html):
    t = re.sub(r"<[^>]+>", " | ", html)
    t = re.sub(r"&#160;|&nbsp;", " ", t)
    t = re.sub(r"&amp;", "&", t)
    t = re.sub(r"[ \t]+", " ", t)
    return re.sub(r"(\| )+", "|", t)


def cmd_revenue():
    out("=== 1082 revenue - per-property revenue from the OBLIGOR's own "
        "audited SEC filings (zero network) ===\n")
    man = read_csv(REVENUE_SOURCE_MANIFEST)
    rows, docs, per_cik = [], 0, {}
    for m in man:
        cik = str(int(m["cik"])) if m["cik"].isdigit() else m["cik"]
        if cik not in REVENUE_CIKS:
            continue
        if m["form"] not in ("10-K", "10-K/A", "S-4", "S-4/A", "10-Q", "424B3"):
            continue
        fp = CEDAR / m["local_file"]
        if not fp.exists():
            continue
        docs += 1
        per_cik[cik] = per_cik.get(cik, 0) + 1
        plain = _flatten(fp.read_text(encoding="utf-8", errors="replace"))
        obligor, nation, uid = REVENUE_CIKS[cik]
        for mt in REV_PAT.finditer(plain):
            pre = plain[max(0, mt.start() - 450):mt.start()]
            best, bp = None, -1
            for prop in REVENUE_PROPERTIES:
                for cand in ("|" + prop + " |", "|" + prop + "|"):
                    i = pre.rfind(cand)
                    if i > bp:
                        bp, best = i, prop
            if best is None or bp < 0:
                continue
            amt = float(mt.group(2).replace(",", ""))
            mult = 1e9 if mt.group(3).lower() == "billion" else 1e6
            fid, fname, st = REVENUE_PROPERTIES[best]
            rows.append({
                "observation_id": "",
                "property_as_published": best,
                "facility_id": fid,
                "facility_name_in_cedar": fname,
                "state": st,
                "obligor_name": obligor,
                "obligor_nation": nation,
                "obligor_cedar_uid": uid,
                "fiscal_year_end_as_published": mt.group(4),
                "fiscal_year": mt.group(4)[-4:],
                "amount_usd": "%.0f" % (amt * mult),
                "amount_as_published": "$%s %s" % (mt.group(2), mt.group(3)),
                "measurement_type": "PROPERTY_NET_REVENUE_INCLUDES_NON_GAMING",
                "measurement_type_basis": (
                    "The filing's own words are \"net revenues\", which is "
                    "TOTAL property revenue and includes hotel, food, "
                    "beverage, entertainment and retail. It is NOT gaming "
                    "revenue and is NOT comparable to NIGC gross gaming "
                    "revenue, which is gaming win only."),
                "assertion_class": "AUDITED_OBLIGOR_SEC_DISCLOSURE",
                "evidence_class": (
                    "the obligor's OWN mandatory SEC periodic report, audited. "
                    "A third evidence class: stronger than a casino's own "
                    "marketing page, and different in kind from an NIGC "
                    "figure - this is a company reporting on itself under "
                    "federal securities law."),
                "not_summable_with": (
                    "NEVER add to nigc_regional_ggr or to any row of "
                    "gaming_revenue_bounds: a REGIONAL_GGR_CEILING is an upper "
                    "bound on this very property, so adding the two adds a "
                    "part to its own whole. NEVER add to a gaming-win figure - "
                    "this number includes non-gaming revenue. NEVER add to "
                    "tribal_debt_holdings.principal_usd or to any deal value."),
                "sovereign_caution": (
                    "The obligor is an instrumentality of a sovereign nation "
                    "and files because of a securities registration, not "
                    "because tribal finances are public. Report the figure, "
                    "the filing and the date; do not characterise the "
                    "nation's finances beyond them."),
                "verbatim_quote": mt.group(0)[:400],
                "source_authority":
                    "U.S. Securities and Exchange Commission, EDGAR",
                "source_document_type": m["form"],
                "source_url": m["document_url"],
                "filing_date": m["file_date"],
                "accession": m["accession"],
                "confidence_tier": "A",
                "confidence_tier_basis": (
                    "the figure is re-readable in the retrieved document and "
                    "the verbatim sentence is carried on the row"),
                "built_by_script": SCRIPT,
                "built_date": TODAY,
                "record_scope":
                    "PROPERTY_REVENUE_OBSERVATION_FROM_AUDITED_FILING",
            })

    # The SAME figure restated in the following year's 10-K is a
    # CORROBORATION, not a second observation. Collapse and count.
    byk = {}
    for r in rows:
        k = (r["property_as_published"], r["fiscal_year"], r["amount_usd"])
        if k in byk:
            byk[k]["corroborating_filings"] = (
                byk[k].get("corroborating_filings", "") + "; "
                + r["accession"]).strip("; ")
            byk[k]["n_independent_filings"] = str(
                int(byk[k].get("n_independent_filings", "1")) + 1)
        else:
            r["corroborating_filings"] = ""
            r["n_independent_filings"] = "1"
            byk[k] = r
    final = sorted(byk.values(),
                   key=lambda r: (r["property_as_published"], r["fiscal_year"]))
    for i, r in enumerate(final, 1):
        r["observation_id"] = "TOPR-%04d" % i

    write_csv(REVENUE_OUT, final, ["observation_id", "property_as_published",
                                   "facility_id", "fiscal_year", "amount_usd"])
    out("  %d obligor documents scanned across %d CIKs" % (docs, len(per_cik)))
    for cik, n in sorted(per_cik.items()):
        out("      %-9s %-42s %3d docs"
            % (cik, REVENUE_CIKS[cik][0][:42], n))
    missing = [c for c in REVENUE_CIKS if c not in per_cik]
    if missing:
        out("\n  NOT ON DISK (NOT_ACQUIRED, a real fetch task, not an absence "
            "in the world):")
        for c in missing:
            out("      %-9s %s" % (c, REVENUE_CIKS[c][0]))
    out("\n  %d distinct property-year revenue observations" % len(final))
    for r in final:
        out("      %-22s FY%s  $%15s  %-12s x%s filings"
            % (r["property_as_published"], r["fiscal_year"],
               format(int(r["amount_usd"]), ","),
               r["facility_id"] or "(no facility)",
               r["n_independent_filings"]))
    ids = sorted({r["facility_id"] for r in final if r["facility_id"]})
    out("\n  Cedar facilities reached: %d  -> %s" % (len(ids), ids))
    out("  wrote %s" % REVENUE_OUT)


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
            "Three independently binding clauses, re-read VERBATIM from "
            "https://emma.msrb.org/AboutEmma/UserAgreement on 2026-09-02 and "
            "cached at data/raw/external/tribal_debt_1082/"
            "emma_user_agreement_2026-09-02.html. Any ONE of them is "
            "sufficient on its own."),
        "clause_1_bars_the_OUTPUT_not_only_the_method": (
            "\"You agree that you will not: use Content or Services to "
            "develop or create a database to be sold, leased, furnished, "
            "licensed or otherwise exploited or made available (either "
            "commercially or free of charge).\" Cedar Press is a paid "
            "product, and note the parenthetical reaches a FREE release too - "
            "so \"publish it for nothing\" is not a way round this clause."),
        "clause_2_names_MANUAL_collection_too": (
            "\"use or allow others to use any data mining, crawling, "
            "'scraping', robot or similar automated or data gathering or "
            "extraction method, OR ANY MANUAL PROCESS, to access, acquire, "
            "monitor or copy any portion of the Website, Content or Services, "
            "or otherwise systematically download or store Content.\" "
            "THIS IS NEW AGAINST THE 2026-08-05 RECORD, which quoted only the "
            "automated half. docs/TRIBAL_DEBT_BUILD_LOG.md ranked \"resolve "
            "the EMMA licence, then work the ~70-issuer roster\" second and "
            "implied a human could read the documents in the meantime. The "
            "clause says otherwise: hand-collection is named. There is no "
            "hand-collection workaround."),
        "clause_3_a_SECOND_licensor_sits_on_top": (
            "\"The CUSIP Database and the information contained therein is "
            "and shall remain valuable intellectual property owned by, or "
            "licensed to, CUSIP Global Services ('CGS') and the American "
            "Bankers Association ('ABA')... Any use by you outside of the "
            "clearing and settlement of transactions requires a license from "
            "CGS, along with an associated fee based on usage.\" EMMA's own "
            "footer also credits ICE Data Pricing & Reference Data, LLC. So "
            "an MSRB licence alone would NOT clear CUSIPs - a second licence "
            "and a usage fee sit behind it. Anyone costing this must cost "
            "both."),
        "robots_txt_as_measured": robots,
        "robots_is_not_the_blocker": (
            "robots.txt was re-measured 2026-09-02 and is unchanged: "
            "\"User-agent: * / Disallow: /*.pdf$\". Only PDFs. A permissive "
            "robots line is NOT permission - the Terms of Use are the binding "
            "instrument and they are far broader than robots."),
        "the_clean_routes_back_in": (
            "(1) ASK. The agreement states its own exception - \"unless "
            "otherwise authorized by the MSRB\" - and names where to write: "
            "Municipal Securities Rulemaking Board, 1300 I Street NW, Suite "
            "1000, Washington, DC 20005, Attention: External Relations, or "
            "MSRBSupport. Cedar's standing principle is that asking is the "
            "route back in and a cleverer scrape is not "
            "(docs/PUBLICATION_POLICY.md). "
            "(2) BUY. MSRB sells subscription data feeds; price CGS beside it. "
            "(3) GO ROUND IT BY AUTHOR, not by route. The same official "
            "statements and continuing disclosures are authored by the "
            "ISSUER, the CONDUIT ISSUER and the UNDERWRITER. A document "
            "obtained from one of THOSE publishers is that publisher's, and "
            "MSRB's terms over its own website do not reach it "
            "(docs/PUBLICATION_POLICY.md, TERMS-SCOPE: \"The distinction is "
            "authorship, not subject matter\"). Caveat, and it cuts the other "
            "way here: because a continuing-disclosure document is filed BY "
            "the obligor, for the eight hard-listed sources their own filings "
            "stay EXCLUDED by that same ruling."),
        "what_is_forgone_measured": (
            "docs/TRIBAL_DEBT_BUILD_LOG.md enumerated roughly 95 tribal "
            "issuer records across ~70 distinct tribal governments on the "
            "EMMA type-ahead, and found the roster is dominated by housing, "
            "health, water and sewer, sales-tax and general governmental "
            "purposes rather than gaming. For the subset that ARE gaming "
            "authority obligors, the annual audited financial statements "
            "would carry facility-level gaming revenue - the figure the "
            "gaming dataset records as SOURCE_DOES_NOT_PUBLISH on 776 of 787 "
            "facilities. That is what this refusal costs, stated plainly so "
            "the owner can price the licence against it."),
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


def _named_invariant_fired(verify_output, invariant_name):
    """Did `verify` report a BREACH against THIS invariant, by name?

    THE BUG THIS REPLACES IS THIS REPO'S SIGNATURE DEFECT, committed in the
    selftest that was supposed to catch it (docs/AGENT_FIELD_GUIDE.md section
    3: "a check that does not measure its own name").

    The first draft tested `"BREACH" in txt.split(name, 1)[1][:12]`. The
    verify line is `"%-58s %s" % (name, verdict)`, so for a 50-character
    invariant name the verdict starts at offset 59 - past the 12-character
    window. The selftest printed "I6 ... DID NOT FIRE" while I6 was in fact
    firing correctly, which would have sent the next reader to debug a working
    invariant. It measured its own string arithmetic, not the invariant.

    Reconstruct the exact line verify prints. Nothing to get wrong."""
    return ("  %-58s %s" % (invariant_name, "BREACH")) in verify_output


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
            ok = (rc == 1) and _named_invariant_fired(txt, name)
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
        ok = (rc == 1) and _named_invariant_fired(txt, name)
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
  revenue     per-property revenue from obligor SEC filings (no network)
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
    elif c == "revenue":
        cmd_revenue()
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
