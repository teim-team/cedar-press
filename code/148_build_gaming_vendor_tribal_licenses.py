#!/usr/bin/env python3
"""148_build_gaming_vendor_tribal_licenses.py -- Gaming spec Step 14.

Gaming supplier disclosure filings: a vendor licensed in a commercial gaming
jurisdiction has to enumerate its licences, and the enumeration includes the
TRIBAL ones. That is a route to a tribal vendor relationship that needs no
tribal source and no vendor cooperation.

=== WHY EDGAR AND NOT A STATE LICENSING PORTAL

A state regulator's public vendor roster tells you the vendor is licensed IN
THAT STATE. The disclosure that names OTHER jurisdictions -- the thing this
step is actually after -- is in the licensing application, and applications are
not public in any state checked. What IS public, signed under Section 302, and
free, is the issuer's own enumeration of its gaming licences in its SEC filings.
`Item 1. Business -- Gaming Regulation` and the S-1/S-4 regulatory appendices
are written precisely to list every jurisdiction the registrant is licensed in,
because omitting one is a securities problem.

EDGAR full-text search covers **2001 onward only**. A vendor relationship that
ended before 2001 is not in this file, and that is a property of the index.

=== THE TWO INFERENCES THIS FILE REFUSES TO MAKE

**1. A mention is not an authorisation.** A 10-K that says "the XYZ Tribal
Gaming Commission requires..." names a regulator; it does not say the registrant
holds its licence. Only a sentence that says the registrant IS licensed,
certified, registered, found suitable or approved by a named tribal regulator
produces `VENDOR_AUTHORIZED_BY_TRIBAL_REGULATOR`. Everything else is
`TRIBAL_REGULATOR_NAMED`, which asserts only that the filing names it.

**2. A licence is not an installation.** The gaming spec is explicit: a
manufacturer or regulator using a different property name is an alias, not a
second property -- and a licence held with a tribe's regulator says nothing
about which of that tribe's properties, if any, carries the vendor's product.
`property_inference` is `REFUSED` on every row, with the reason on the row.

Related, already standing: **manufacturer revenue per participation unit
measures the manufacturer's economics, not the casino's GGR.** Where a supplier
filing reports participation revenue, that is the VENDOR's revenue. It is not
`MACHINE_PARTICIPATION_EXPENSE`, which is the tribal operator's expense, and
the two are never written into the same column. This build emits no
`MACHINE_PARTICIPATION_EXPENSE` at all; that measure comes from the operator's
audited statements, not the vendor's.

=== STATE REGULATORS ARE FILTERED OUT BY NAME, AND THE LIST IS EXPLICIT

"Nevada Gaming Commission", "Michigan Gaming Control Board", "Pennsylvania
Gaming Control Board" all match a naive `\\w+ Gaming Commission` pattern. So does
"National Indian Gaming Commission", which is FEDERAL and is not a tribal
regulator. Both classes are excluded by an enumerated list rather than by a
heuristic, and the exclusions are counted so the filter's reach is visible.

Reads  efts.sec.gov  (EDGAR full-text search, 2001+)
       www.sec.gov    (filing documents)
       data/spine/cedar_entity_spine.csv
Writes data/clean/gaming_vendor_tribal_licenses.csv
       data/clean/source_coverage_vendor_disclosure.csv
       review/vendor_disclosure_unresolved_regulators.csv
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

import requests

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
RAW = ROOT / "data" / "raw" / "sec_vendor_disclosure"
TXT = RAW / "txt"
CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
SCRIPT = "code/148_build_gaming_vendor_tribal_licenses.py"
TODAY = dt.date.today().isoformat()
NOW = dt.datetime.now(dt.timezone.utc).isoformat()
for d in (RAW, TXT, CLEAN, REVIEW, LOGS):
    d.mkdir(parents=True, exist_ok=True)

FTS_HOST = "efts.sec.gov"
DOC_HOST = "www.sec.gov"
UA = "CedarPress-research elijahsamsonmoreno@gmail.com"
HDR = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
GAP = 0.5
DEADLINE_S = 45 * 60
DISK_FLOOR_GB = 6.0
MAX_DOC_BYTES = 28 * 1024 * 1024
DOC_BUDGET = int(os.environ.get("SEC_DOC_BUDGET", "300"))
START = time.time()

QUERIES = [
    ('"Tribal Gaming Commission"', "10-K"),
    ('"Tribal Gaming Commission"', "S-1"),
    ('"Tribal Gaming Commission"', "S-4"),
    ('"tribal gaming commissions"', ""),
    ('"Tribal Gaming Agency"', ""),
    ('"Tribal Gaming Authority"', ""),
    ('"Tribal Gaming Office"', ""),
    ('"Tribal Gaming Regulatory Authority"', ""),
    ('"licensed by the tribal"', ""),
    ('"tribal gaming licenses"', ""),
]

# Excluded by enumeration, not by heuristic.
FEDERAL_OR_STATE = {
    "national indian", "nevada gaming", "michigan gaming",
    "pennsylvania gaming", "new jersey", "colorado gaming", "illinois gaming",
    "indiana gaming", "iowa racing", "kansas racing", "louisiana gaming",
    "mississippi gaming", "missouri gaming", "new mexico gaming",
    "new york state gaming", "ohio casino", "oklahoma horse racing",
    "west virginia lottery", "arizona department of gaming",
    "california gambling control", "washington state gambling",
    "state gaming", "state of", "united states", "u.s.", "federal",
    "provincial", "ontario", "british columbia", "alberta", "quebec",
    "puerto rico", "district of columbia", "european", "united kingdom",
    "gambling commission of", "the gaming", "our gaming", "such gaming",
    "each gaming", "any gaming", "a gaming", "an gaming", "applicable gaming",
    "other gaming", "certain gaming", "various gaming", "relevant gaming",
    "respective gaming", "local gaming", "indian gaming", "class ii gaming",
    "class iii gaming", "internet gaming", "online gaming", "interactive gaming",
}

# A regulator's name is <tribe name> + <regulator suffix>. The tribe name is
# capitalised tokens, possibly with internal particles (Sault Ste. Marie, Band
# of Mission Indians, Prairie Island Indian Community). Capturing that means
# capturing particles, and a particle at the START is the article of the
# surrounding sentence ("the Mohegan Tribal Gaming Authority"), not part of the
# name. The first version of this rejected any capture beginning with a
# lowercase word, which threw away 93 Mohegan and 36 Mescalero Apache matches
# -- the filter fired on the sentence's own definite article. Strip leading
# particles; do not reject on them.
_TOK = r"(?:[A-Z][A-Za-z'’\.\-]*|of|the|and|de|del|du|d')"
REG_RE = re.compile(
    r"((?:%s[ \-]){1,7})"
    r"(Tribal\s+Gaming\s+(?:Commission|Agency|Authority|Office|"
    r"Regulatory\s+Authority|Board)|Gaming\s+(?:Commission|Agency|Authority|"
    r"Regulatory\s+Authority|Office))" % _TOK)

LEAD_PARTICLE = re.compile(r"^(?:(?:by|of|from|with|to|and|at|the|a|an|its|"
                           r"our|their|each|any|such|other|certain|various|"
                           r"applicable|respective|relevant|local|"
                           r"appropriate)\s+)+", re.I)
# A run-on capture swallows the tail of the preceding clause: "Indians Office
# of Gaming Regulations Prairie Island Gaming Commission". Where a regulator
# suffix word appears INSIDE the prefix, the real name starts after it.
INNER_SUFFIX = re.compile(
    r".*\b(?:Commission|Authority|Regulations?|Board|Agency|Office)\b\s*",
    re.S)

AUTH_RE = re.compile(
    r"\b(?:is|are|was|were|has\s+been|have\s+been|holds?|hold|maintains?|"
    r"received|obtained|granted)\b[^.;]{0,120}?"
    r"\b(licen[cs]ed|licen[cs]e|certified|certification|registered|"
    r"registration|found\s+suitable|suitability|approved|approval|permitted)\b",
    re.I)

LIC_NUM = re.compile(r"\b(?:licen[cs]e|cert(?:ificate|ification)?|permit)\s*"
                     r"(?:no\.?|number|#)\s*[:\-]?\s*([A-Z0-9\-/]{3,20})", re.I)
DATE_RE = re.compile(
    r"\b((?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})")

SENT = re.compile(r"(?<=[.;])\s+")
TAG = re.compile(r"<[^>]+>")
SCRIPT_STYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)


# --------------------------------------------------------------------------
def lock_path(host):
    return LOGS / ("_HOSTLOCK_%s.json" % host)


def read_lock(host):
    p = lock_path(host)
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


def claim_host(host, purpose):
    cur = read_lock(host)
    if cur and cur.get("active") and not cur.get("released"):
        if cur.get("pid") and pid_alive(cur["pid"]):
            cur.setdefault("queue", []).append(
                {"script": SCRIPT, "purpose": purpose, "queued_at": NOW})
            lock_path(host).write_text(json.dumps(cur, indent=1),
                                       encoding="utf-8")
            print("  host busy, queued: %s" % host)
            return False
    lock_path(host).write_text(json.dumps({
        "host": host, "pid": os.getpid(), "script": SCRIPT, "claimed_at": NOW,
        "active": True, "queue": [],
        "policy": "sequential, single poller, %.1fs gap, stop on first edge "
                  "refusal" % GAP,
        "note": purpose}, indent=1), encoding="utf-8")
    return True


def release_host(host, note_text=""):
    cur = read_lock(host) or {"host": host}
    cur.update({"active": False, "released": TODAY, "note": note_text})
    lock_path(host).write_text(json.dumps(cur, indent=1), encoding="utf-8")


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


# --------------------------------------------------------------------------
class Sec:
    def __init__(self):
        self.s = requests.Session()
        self.n = 0
        self.consec = 0

    def get(self, url, params=None, stream=False):
        if out_of_time():
            raise SystemExit and None
        for attempt in range(3):
            try:
                r = self.s.get(url, params=params, headers=HDR, timeout=(15, 180),
                               stream=stream)
            except Exception as e:
                self.consec += 1
                print("    TRANSPORT %s" % e)
                if self.consec >= 3:
                    raise RuntimeError("three transport failures")
                time.sleep(15 * (attempt + 1))
                continue
            self.n += 1
            time.sleep(GAP)
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(20 * (attempt + 1))
                continue
            self.consec = 0
            return r
        return None


def fts(sec, q, forms):
    """-> list of hit dicts. EDGAR FTS pages 10 at a time via `from`."""
    hits, frm = [], 0
    while frm < 200:
        p = {"q": q, "from": frm}
        if forms:
            p["forms"] = forms
        r = sec.get("https://efts.sec.gov/LATEST/search-index", params=p)
        if r is None or r.status_code != 200:
            print("    fts %-38s forms=%-5s HTTP %s"
                  % (q, forms or "-", getattr(r, "status_code", 0)))
            break
        try:
            j = r.json()
        except Exception:
            break
        h = (j.get("hits") or {}).get("hits") or []
        total = ((j.get("hits") or {}).get("total") or {}).get("value")
        if frm == 0:
            print("    fts %-38s forms=%-5s total=%s" % (q, forms or "-", total))
        if not h:
            break
        hits.extend(h)
        frm += len(h)
        if len(h) < 10:
            break
    return hits


def doc_url(hit):
    """EDGAR FTS `_id` is `<accession-with-dashes>:<filename>`."""
    _id = hit.get("_id") or ""
    if ":" not in _id:
        return None, None, None
    acc, fn = _id.split(":", 1)
    cik = (hit.get("_source", {}).get("ciks") or ["0"])[0]
    accn = acc.replace("-", "")
    return ("https://www.sec.gov/Archives/edgar/data/%d/%s/%s"
            % (int(cik), accn, fn)), acc, fn


def to_text(b):
    t = b.decode("utf-8", "replace")
    t = SCRIPT_STYLE.sub(" ", t)
    t = TAG.sub(" ", t)
    t = htmlmod.unescape(t)
    return re.sub(r"[ \t\xa0]+", " ", t)


# PASS 2 FIXES, EACH FROM A MEASURED FALSE POSITIVE IN PASS 1.
#
#   "Chief Executive Officer of the Mohegan Tribal Gaming Authority"   32 rows
#   "Press Release of the Mohegan Tribal Gaming Authority"             57
#   "Table of Contents The Tribal Gaming Commission"
#   "Total Mohegan Tribal Gaming Authority"                            21
#   "Chairman of the National Indian Gaming Commission"
#   "Nevada Gaming Commission" / "Indiana" / "Mississippi" / "Massachusetts"
#
# Two distinct defects. The prefix captured the tail of the preceding clause
# (fixed by cutting at the LAST connective particle rather than stripping only
# a leading one), and the federal/state exclusion was tested against the PREFIX
# while every entry in the list names the full institution (fixed by testing
# the assembled name).
PARTICLE_SPLIT = re.compile(
    r"(?i)\b(?:of\s+the|of|the|and|by|for|to|at|in|from|its|our|their|a|an)\b")
DOC_FURNITURE = {"total", "press", "release", "table", "contents", "item",
                 "note", "notes", "chairman", "chairwoman", "chief",
                 "executive", "officer", "financial", "operating", "president",
                 "director", "none", "q", "part", "exhibit", "schedule",
                 "annual", "quarterly", "report", "form", "index", "summary",
                 "source", "see", "signature", "signatures"}
STATE_PROV = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming", "ontario",
    "alberta", "quebec", "manitoba", "saskatchewan", "alcohol"}


def classify_regulator(prefix, tail):
    """-> full regulator name, or None (the caller counts the refusal)."""
    p = prefix.strip()
    parts = PARTICLE_SPLIT.split(p)
    p = parts[-1].strip(" ,.-")
    m = INNER_SUFFIX.match(p)
    if m and m.end() < len(p):
        p = p[m.end():].strip(" ,.-")
    toks = p.split()
    while toks and toks[0].lower() in DOC_FURNITURE:
        toks.pop(0)
    p = " ".join(toks)
    if len(p) < 4 or not p[:1].isupper():
        return None
    low = p.lower()
    if low in {"indian", "indians", "tribal", "tribe", "nation", "class",
               "gaming", "casino", "resort", "band", "authority", "commission"}:
        return None
    for st in STATE_PROV:
        if low == st or low.startswith(st + " "):
            return None
    full = p + " " + re.sub(r"\s+", " ", tail.strip())
    flow = full.lower()
    for bad in FEDERAL_OR_STATE:
        if flow.startswith(bad):
            return None
    # "Every State Gaming Agency" is a compact's generic term for the state
    # regulator, not a named tribal one. Caught in pass 2.
    if re.search(r"\bstate gaming (?:agency|agencies|authority|commission)\b",
                 flow):
        return None
    return full


def main():
    print("148 gaming supplier disclosure -> tribal regulator licences  "
          "free=%.1f GB" % free_gb())
    spine = read_csv(ROOT / "data" / "spine" / "cedar_entity_spine.csv")
    rez = load_resolver()
    print("  spine %d entities" % len(spine))

    cache_f = RAW / "fts_hits.json"
    hits = []
    if cache_f.exists() and "--refresh" not in sys.argv:
        hits = json.loads(cache_f.read_text(encoding="utf-8"))
        print("  fts hits from cache: %d" % len(hits))
    else:
        if not claim_host(FTS_HOST, "EDGAR full-text search: tribal gaming "
                                    "regulator names in supplier filings"):
            return 1
        sec = Sec()
        try:
            for q, forms in QUERIES:
                hits.extend(fts(sec, q, forms))
        except RuntimeError as e:
            print("  STOP-WORK on %s: %s" % (FTS_HOST, e))
        finally:
            release_host(FTS_HOST, "full-text search complete")
        cache_f.write_text(json.dumps(hits), encoding="utf-8")

    # dedupe on document identity
    uniq = {}
    for h in hits:
        uniq.setdefault(h.get("_id"), h)
    docs = list(uniq.values())
    print("  %d hits -> %d distinct documents" % (len(hits), len(docs)))

    # ---- fetch documents -------------------------------------------------
    fetched = []
    if claim_host(DOC_HOST, "EDGAR filing documents for tribal-regulator "
                            "extraction"):
        sec = Sec()
        n_new = n_skip = n_fail = 0
        try:
            for h in docs[:DOC_BUDGET]:
                if out_of_time() or free_gb() < DISK_FLOOR_GB:
                    print("  stopping document fetch (deadline or disk)")
                    break
                url, acc, fn = doc_url(h)
                if not url:
                    continue
                local = TXT / ((acc or "x") + "_" + re.sub(r"[^\w.\-]", "_",
                                                           fn or "x") + ".txt")
                if local.exists():
                    n_skip += 1
                    fetched.append((h, url, local))
                    continue
                r = sec.get(url, stream=True)
                if r is None or r.status_code != 200:
                    n_fail += 1
                    continue
                buf, n = [], 0
                for chunk in r.iter_content(1 << 16):
                    buf.append(chunk)
                    n += len(chunk)
                    if n > MAX_DOC_BYTES:
                        break
                r.close()
                if n > MAX_DOC_BYTES:
                    n_fail += 1
                    continue
                local.write_text(to_text(b"".join(buf)), encoding="utf-8")
                n_new += 1
                fetched.append((h, url, local))
                if n_new % 40 == 0:
                    print("    docs %d new / %d cached  free=%.1fGB"
                          % (n_new, n_skip, free_gb()))
        except RuntimeError as e:
            print("  STOP-WORK on %s: %s" % (DOC_HOST, e))
        finally:
            release_host(DOC_HOST, "filing documents fetched")
        print("  documents: %d new, %d cached, %d not retrieved"
              % (n_new, n_skip, n_fail))

    # ---- extract ---------------------------------------------------------
    rows, unresolved, excl = [], {}, Counter()
    for h, url, local in fetched:
        src = h.get("_source") or {}
        issuer = (src.get("display_names") or ["?"])[0]
        issuer_name = re.sub(r"\s*\(.*$", "", issuer).strip()
        form = src.get("root_forms") or src.get("file_type") or ""
        filed = src.get("file_date") or ""
        cik = (src.get("ciks") or [""])[0]
        try:
            text = local.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        # Is the issuer itself a Native entity? Then it is not a vendor row.
        iid, iname, ihow = rez(issuer_name, spine)
        issuer_is_native = bool(iid)
        for sent in SENT.split(text):
            s = re.sub(r"\s+", " ", sent).strip()
            if len(s) < 25 or len(s) > 1200:
                continue
            if "gaming" not in s.lower():
                continue
            found = []
            for m in REG_RE.finditer(s):
                reg = classify_regulator(m.group(1), m.group(2))
                if not reg:
                    excl[(m.group(1).strip().lower()[:40])] += 1
                    continue
                found.append(reg)
            if not found:
                continue
            # PROSPECTIVE IS NOT HELD. The same rule the capacity build uses
            # for PROJECTED device counts applies to licences: IGT's 2001 10-K
            # says a merger "is subject to the approval of ... the Pala Gaming
            # Commission", which is a licence NOT yet held, and pass 2 typed it
            # VENDOR_AUTHORIZED. A forward-looking clause voids the
            # authorisation reading.
            prospective = re.search(
                r"\b(subject\s+to|will\s+be\s+required|must\s+(?:obtain|be)|"
                r"has\s+applied|have\s+applied|is\s+applying|pending|intends?\s+"
                r"to|expects?\s+to|anticipat\w+|prior\s+to\s+(?:the\s+)?"
                r"commencement|cannot\s+assure)\b", s, re.I)
            authorised = bool(AUTH_RE.search(s)) and not prospective
            lic = LIC_NUM.search(s)
            dates = DATE_RE.findall(s)
            for reg in dict.fromkeys(found):
                tribe_str = re.sub(
                    r"\s+(Tribal\s+)?Gaming\s+(Commission|Agency|Authority|"
                    r"Office|Regulatory\s+Authority|Board)$", "", reg).strip()
                eid, ename, how = rez(tribe_str, spine)
                if not eid:
                    unresolved[tribe_str] = unresolved.get(tribe_str, 0) + 1
                rows.append({
                    "vendor_name": issuer_name,
                    "vendor_cik": cik,
                    "vendor_is_native_entity": int(issuer_is_native),
                    "vendor_native_entity_id": iid or "",
                    "tribal_gaming_regulator": reg,
                    "tribal_gaming_regulator_tribe_string": tribe_str,
                    "entity_id": eid or "",
                    "entity_name": ename or "",
                    "entity_match_method": how,
                    "entity_tier": ("B" if str(how).startswith("contain")
                                    else ("A" if eid else "")),
                    "license_type": ("named in filing; type not stated in the "
                                     "quoted sentence"),
                    "license_number": lic.group(1) if lic else "",
                    "application_date": "",
                    "approval_date": "",
                    "dates_in_quote": "|".join(dates[:4]),
                    # A tribal gaming authority filing its OWN 10-K and naming
                    # itself is not a vendor relationship. Mohegan Tribal
                    # Gaming Authority alone produced 234 such rows in pass 1,
                    # all of them the issuer talking about itself.
                    "status": (
                        "SELF_REFERENCE_NOT_A_VENDOR_RELATIONSHIP"
                        if (issuer_is_native and eid and eid == iid)
                        else "VENDOR_AUTHORIZED_BY_TRIBAL_REGULATOR"
                        if authorised and not issuer_is_native
                        else "TRIBAL_REGULATOR_NAMED"),
                    "status_basis": (
                        "the registrant IS this tribal entity; the filing "
                        "names its own regulator"
                        if (issuer_is_native and eid and eid == iid) else
                        "the quoted sentence states the registrant is "
                        "licensed / certified / registered / found suitable / "
                        "approved" if authorised and not issuer_is_native else
                        "the filing NAMES this regulator; it does not state "
                        "that the registrant holds its licence. A mention is "
                        "not an authorisation."),
                    "property_inference": "REFUSED",
                    "property_inference_basis": (
                        "A licence held with a tribe's gaming regulator does "
                        "not establish that the vendor's product is installed "
                        "at any property. That needs a second source."),
                    "measurement_type": "",
                    "measurement_type_basis": (
                        "This row is a licensing relationship, not a financial "
                        "measure. Where a supplier filing reports "
                        "participation REVENUE that is the vendor's economics "
                        "and is NOT MACHINE_PARTICIPATION_EXPENSE, which is "
                        "the tribal operator's expense."),
                    "confidence_tier": "A" if authorised and eid else "B",
                    "source_authority": "U.S. Securities and Exchange "
                                        "Commission, EDGAR",
                    "source_document_type": "sec_filing_%s" % (form or "doc"),
                    "form_type": form,
                    "filed_date": filed,
                    "source_url": url,
                    "retrieved_at": TODAY,
                    "verbatim_quote": s,
                    "built_date": TODAY,
                })

    # dedupe (vendor, regulator, filing)
    seen, out = set(), []
    for r in rows:
        k = (r["vendor_cik"], r["tribal_gaming_regulator"], r["source_url"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    write_csv(CLEAN / "gaming_vendor_tribal_licenses.csv", out)

    write_csv(REVIEW / ("vendor_disclosure_unresolved_regulators_%s.csv"
                        % TODAY),
              [{"regulator_tribe_string": k, "n_rows": v,
                "reason": "no spine match via resolve_entity"}
               for k, v in sorted(unresolved.items(), key=lambda kv: -kv[1])])

    auth = [r for r in out if r["status"] ==
            "VENDOR_AUTHORIZED_BY_TRIBAL_REGULATOR"]
    vendors = {r["vendor_name"] for r in out if not r["vendor_is_native_entity"]}
    ents = {r["entity_id"] for r in out if r["entity_id"]}
    cov = [
        {"source": "SEC EDGAR full-text search", "host": "efts.sec.gov",
         "facet": "supplier filings naming a tribal gaming regulator",
         "status": "PUBLISHES", "n": len(docs),
         "evidence": "%d distinct documents surfaced by %d phrase queries; "
                     "%d fetched and parsed."
                     % (len(docs), len(QUERIES), len(fetched)),
         "coverage_floor": "EDGAR full-text search indexes 2001 onward. A "
                           "vendor relationship disclosed only before 2001 is "
                           "absent from this file as a property of the index.",
         "retrieved_at": TODAY,
         "source_url": "https://efts.sec.gov/LATEST/search-index"},
        {"source": "State gaming regulator licensing APPLICATIONS",
         "host": "(multiple)",
         "facet": "an applicant's enumeration of licences held in other "
                  "jurisdictions, including tribal",
         "status": "NOT_CHECKED", "n": 0,
         "evidence": "Applications and multi-jurisdictional personal history "
                     "disclosure forms are the document that carries licence "
                     "numbers and application dates. No state checked here "
                     "publishes them. Rosters that ARE published name only "
                     "that state's own licence.",
         "coverage_floor": "", "retrieved_at": TODAY, "source_url": ""},
    ]
    write_csv(CLEAN / "source_coverage_vendor_disclosure.csv", cov)

    print("\n=== 148 SUMMARY ===")
    print("  documents parsed              %6d" % len(fetched))
    print("  rows                          %6d" % len(out))
    print("    VENDOR_AUTHORIZED           %6d" % len(auth))
    print("    TRIBAL_REGULATOR_NAMED      %6d" % (len(out) - len(auth)))
    print("  distinct non-Native vendors   %6d" % len(vendors))
    print("  distinct spine entities       %6d" % len(ents))
    print("  unresolved regulator strings  %6d" % len(unresolved))
    print("  filtered as federal/state     %6d occurrences, %d strings"
          % (sum(excl.values()), len(excl)))
    for k, v in excl.most_common(10):
        print("     excluded %-42s %d" % (k, v))
    return 0


if __name__ == "__main__":
    sys.exit(main())
