#!/usr/bin/env python3
r"""
Cedar Press - 96: Tribal consultation events (Government Relations & Advocacy, ch. CONSULTATION).

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
Tribal consultation is a **statutory government-to-government obligation**
(E.O. 13175, NHPA s.106, NAGPRA 25 U.S.C. 3003, agency consultation policies).
It is **not lobbying**. `cedar_domain.AdvocacyChannel.CONSULTATION.is_lobbying`
returns False and this script never writes any other channel onto a
consultation row. Filing a sovereign's statutory consultation under "lobbying"
would characterise a government-to-government relationship as influence-buying.

The dataset this feeds is therefore *government relations and advocacy*, with
`channel` explicit on every row.

WHAT IT EXTENDS
---------------
The Federal Register pass already on disk:
    data/clean/fr_consultation_notices.csv     484 notices
    data/clean/fr_consultation_referenced.csv  1,829 records reporting
                                               consultation already undertaken
    data/clean/fr_consultation_by_agency.csv   21 agencies
    data/clean/fr_consultation_year.csv        33 years
Those four files are INPUTS. This script never writes to them.

This script goes from *notice-level* to *participant-level*: it retrieves the
full published text of every one of those 2,313 documents and extracts who was
actually consulted, who was merely invited, when, where, in what format, and
under what deadline.

THE PARTICIPANT GOLDMINE, AND WHY IT IS TRUSTWORTHY
---------------------------------------------------
NAGPRA notices carry a `Consultation` section with a fixed grammar:

    "A detailed assessment ... was made by ... professional staff in
     consultation with representatives of the Arapahoe Tribe of the Wind
     River Reservation, Wyoming; Comanche Nation, Oklahoma; ... and the Ute
     Mountain Tribe of the Ute Mountain Reservation, Colorado, New Mexico &
     Utah. The Hopi Tribe of Arizona; Navajo Nation, Arizona, New Mexico &
     Utah; ... and the Zuni Tribe of the Zuni Reservation, New Mexico, were
     contacted for consultation purposes but did not attend the consultation
     meetings."                                       - 76 FR 7232 (2011-2793)

Two lists, two different facts, in adjacent sentences. The first list
participated. The second list did not. **A tribe invited is not a tribe
present**, and this parser will not let one become the other: role is assigned
from the governing verb phrase in the *same sentence* as the name list, and a
name list in a sentence with no role marker is not extracted at all.

Tribe names in these notices are the official Federal Register list names,
which is why they resolve cleanly against `spine.fr_official_name`.

RESOLUTION GUARDS (the containment defect, AGENTS.md)
-----------------------------------------------------
`resolve_entity` is imported from `code/33_apply_party_rulings.py` - the ONE
resolver, never re-implemented. But its containment tier is unsafe in the
entity-contains-record direction (CHICKASAW NATION -> Chickasaw Children's
Village). Consultation records are the *long* official names and the spine
holds *short* canonical ones, so the safe direction is the only one we need:

  * containment is accepted ONLY when core(record) is a superset of
    core(spine_name) - the record must be at least as specific as the entity.
    The reverse direction is refused outright.
  * where the record names a state and the spine row carries one, the states
    must agree.
  * where the overlap consists only of `cedar_domain.NAME_TRAPS` tokens, the
    match is refused.
  * only government-class spine rows may be a consultation participant. A
    consulting party in a NAGPRA notice is a sovereign, not a CDFI or a school.

Everything refused goes to review/ with its reason. Never a guess.

ABSENCE IS NOT ABSENCE
----------------------
`consultation_agency_coverage.csv` records what each agency publishes,
INCLUDING the agencies that publish nothing we could retrieve. Agencies publish
unevenly; an agency with no retrievable consultation record is a coverage gap,
not evidence that it held no consultations. Every zero in that file carries the
probe evidence that produced it.

USAGE
-----
    py -3 code/96_build_consultation_events.py fetch      # FR text + metadata
    py -3 code/96_build_consultation_events.py agencies   # agency pages+policies
    py -3 code/96_build_consultation_events.py build      # parse -> data/clean/

Reads  data/clean/fr_consultation_notices.csv       (never written)
       data/clean/fr_consultation_referenced.csv    (never written)
       data/spine/cedar_entity_spine.csv            (never written)
       data/clean/native_entity_lobbying_disclosures.csv  (LDA overlap only)
Writes data/clean/consultation_events.csv
       data/clean/consultation_agency_coverage.csv
       review/consultation_unresolved_<date>.csv
       data/raw/external/consultation/**            (cache + fetch manifest)
"""

import csv
import importlib.util
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE_DIR = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
RAW = CEDAR / "data" / "raw" / "external" / "consultation"
FRTEXT = RAW / "fr_text"
TODAY = date.today().isoformat()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

csv.field_size_limit(min(sys.maxsize, 2147483647))

# ---------------------------------------------------------------------------
# THE ONE RESOLVER + THE SHARED VOCABULARY. Imported, never re-declared.
# ---------------------------------------------------------------------------
sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import AdvocacyChannel, Tier, NAME_TRAPS      # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "party_rulings", CEDAR / "code" / "33_apply_party_rulings.py")
_party = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_party)
resolve_entity = _party.resolve_entity
norm = _party.norm
core = _party.core

assert AdvocacyChannel.CONSULTATION.is_lobbying is False, \
    "cedar_domain says consultation is lobbying - refusing to build."

CHANNEL = AdvocacyChannel.CONSULTATION.value


# ===========================================================================
# HOST DISCIPLINE - docs/PULL_DISCIPLINE.md. One poller per host, ever.
# ===========================================================================

def hostlock_path(host):
    return LOGS / f"_HOSTLOCK_{host}.json"


def claim_host(host, script, note):
    """Claim a host, or refuse. Returns True when we may fetch from it."""
    p = hostlock_path(host)
    if p.exists():
        d = json.loads(p.read_text(encoding="utf-8"))
        holder = d.get("holder") or {}
        active = d.get("active") and not d.get("released")
        if active and holder.get("script") and holder["script"] != script:
            d.setdefault("queue", []).append(
                {"requested_by": script, "requested_at": TODAY, "work": note})
            p.write_text(json.dumps(d, indent=2), encoding="utf-8")
            print(f"  [hostlock] {host} HELD by {holder['script']} - queued, not fetching")
            return False
    else:
        d = {"host": host, "queue": []}
    d["holder"] = {"script": script, "claimed": TODAY, "note": note}
    d["active"] = True
    d["policy"] = "sequential, >=0.8s gap, exponential backoff 60s->1800s, stop at ~2h"
    d.pop("released", None)
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"  [hostlock] {host} claimed by {script}")
    return True


def release_host(host, script, note):
    p = hostlock_path(host)
    if not p.exists():
        return
    d = json.loads(p.read_text(encoding="utf-8"))
    if (d.get("holder") or {}).get("script") != script:
        return
    d["active"] = False
    d["released"] = TODAY
    d["note"] = note
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")
    print(f"  [hostlock] {host} released")


MANIFEST = []
_last_hit = defaultdict(float)


def fetch(url, min_gap=0.8, timeout=60, tries=4):
    """Sequential GET with per-host spacing and exponential backoff.

    CHECK THE HTTP STATUS, NOT THE FILE (AGENTS.md): a 404 body still has
    content, so the status travels with every byte we keep and anything that is
    not 200 is refused downstream.
    """
    host = urllib.parse.urlparse(url).netloc
    delay = 60.0
    for attempt in range(tries):
        gap = min_gap - (time.time() - _last_hit[host])
        if gap > 0:
            time.sleep(gap)
        _last_hit[host] = time.time()
        t0 = time.time()
        # Several federal sites (hhs.gov, usda.gov, transportation.gov,
        # usace.army.mil, fcc.gov) sit behind an edge WAF that answers a bare
        # UA-only request with 403. A full browser header set is the difference
        # between "the agency publishes nothing" and "we asked wrongly", and
        # the distinction is the whole point of the coverage file.
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
                      "image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "identity",
            "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1", "Connection": "close",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                MANIFEST.append({"url": url, "http_status": r.status,
                                 "bytes": len(body), "fetched_date": TODAY})
                return r.status, body
        except urllib.error.HTTPError as e:
            MANIFEST.append({"url": url, "http_status": e.code, "bytes": 0,
                             "fetched_date": TODAY})
            if e.code in (429, 503):
                ra = e.headers.get("Retry-After")
                time.sleep(float(ra) if ra and ra.isdigit() else delay)
                delay = min(delay * 2, 1800)
                continue
            return e.code, b""            # 404 etc: a real answer, not a retry
        except Exception as e:
            elapsed = time.time() - t0
            MANIFEST.append({"url": url, "http_status": 0, "bytes": 0,
                             "fetched_date": TODAY})
            if elapsed < 1.0:
                # instant disconnect = EDGE BLOCK. More requests extend it.
                print(f"    [edge-block suspected] {host}: {type(e).__name__} "
                      f"after {elapsed:.2f}s")
                if attempt >= 1:
                    return 0, b""
            time.sleep(delay)
            delay = min(delay * 2, 1800)
    return 0, b""


def save_manifest():
    RAW.mkdir(parents=True, exist_ok=True)
    p = RAW / "_SOURCE_MANIFEST.csv"
    old = read_csv(p)
    seen = {r["url"] for r in old}
    rows = old + [r for r in MANIFEST if r["url"] not in seen]
    write_csv(p, rows, ["url", "http_status", "bytes", "fetched_date"])


# ===========================================================================
# IO
# ===========================================================================

def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


# ===========================================================================
# STAGE 1 - FETCH the full published text of every FR consultation document
# ===========================================================================

FR_HOST = "www.federalregister.gov"
META_FIELDS = ["document_number", "publication_date", "raw_text_url", "title",
               "agencies", "dates", "comments_close_on", "citation",
               "html_url", "type", "abstract", "docket_ids", "action",
               "regulations_dot_gov_url", "comment_url"]


def fr_document_numbers():
    notices = read_csv(CLEAN / "fr_consultation_notices.csv")
    refd = read_csv(CLEAN / "fr_consultation_referenced.csv")
    out = {}
    for r in notices:
        out[r["document_number"]] = "notice"
    for r in refd:
        out.setdefault(r["document_number"], "referenced")
    return out, notices, refd


def stage_fetch():
    print("=== 96 stage FETCH: Federal Register full text ===\n")
    docs, notices, refd = fr_document_numbers()
    print(f"consultation notices        : {len(notices):,}")
    print(f"records reporting consultation: {len(refd):,}")
    print(f"distinct documents to retrieve: {len(docs):,}\n")

    if not claim_host(FR_HOST, "code/96_build_consultation_events.py",
                      "consultation events: metadata + full text for "
                      f"{len(docs):,} FR documents"):
        return

    FRTEXT.mkdir(parents=True, exist_ok=True)
    meta_path = RAW / "fr_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    # ---- 1a. bulk metadata --------------------------------------------------
    # 200 document numbers per request returns HTTP 414 (URI too long): each
    # `conditions[document_numbers][]=` pair costs ~49 URL-encoded characters,
    # so 200 overruns the server's request-line limit. 60 keeps the URI near
    # 3 kB and cuts 2,313 metadata calls to 39.
    CHUNK = 60
    need = [d for d in docs if d not in meta]
    print(f"metadata to fetch: {len(need):,}")
    for i in range(0, len(need), CHUNK):
        chunk = need[i:i + CHUNK]
        q = [("per_page", "1000")] + [("fields[]", f) for f in META_FIELDS]
        q += [("conditions[document_numbers][]", d) for d in chunk]
        url = f"https://{FR_HOST}/api/v1/documents.json?" + urllib.parse.urlencode(q)
        st, body = fetch(url, timeout=120)
        if st != 200:
            print(f"  metadata chunk {i}: HTTP {st} - skipped")
            continue
        for r in json.loads(body)["results"]:
            meta[r["document_number"]] = r
        print(f"  metadata {min(i+CHUNK, len(need)):,}/{len(need):,}")
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    print(f"metadata on disk: {len(meta):,}\n")

    # ---- 1b. full text, sequential, checkpointed --------------------------
    todo = [d for d in docs if not (FRTEXT / f"{d}.txt").exists()]
    print(f"full text to fetch: {len(todo):,}")
    got = miss = 0
    for i, dn in enumerate(todo, 1):
        m = meta.get(dn) or {}
        u = m.get("raw_text_url")
        if not u:
            miss += 1
            continue
        st, body = fetch(u)
        if st == 200 and body:
            (FRTEXT / f"{dn}.txt").write_bytes(body)
            got += 1
        else:
            miss += 1
            (FRTEXT / f"{dn}.MISSING").write_text(str(st), encoding="utf-8")
        if i % 100 == 0:
            print(f"  {i:,}/{len(todo):,}  ok={got:,} miss={miss:,}")
            save_manifest()
    print(f"\nfull text retrieved: {got:,}   unavailable: {miss:,}")
    save_manifest()
    release_host(FR_HOST, "code/96_build_consultation_events.py",
                 f"Consultation build complete: {got:,} full texts retrieved "
                 f"at 0.8s spacing. Lock released.")


# ===========================================================================
# STAGE 2 - AGENCY consultation pages, policies, and published reports
# ===========================================================================
#
# Every URL here was chosen because it is the agency's own consultation
# landing page or policy document. Each is probed, its HTTP status recorded,
# and the result - INCLUDING a 404 or a block - written to
# consultation_agency_coverage.csv. An agency that publishes nothing we can
# retrieve is a COVERAGE GAP, recorded as such, never read as "no
# consultations happened".

AGENCY_PAGES = [
    # (agency_key, agency_label, kind, url)
    ("BIA",   "Interior - Bureau of Indian Affairs", "consultation_hub",
     "https://www.bia.gov/service/tribal-consultations"),
    ("BIA",   "Interior - Bureau of Indian Affairs", "policy",
     "https://www.bia.gov/policy-forms/manual"),
    ("DOI",   "Department of the Interior", "consultation_hub",
     "https://www.doi.gov/priorities/strengthening-tribal-nations"),
    ("DOI",   "Department of the Interior", "consultation_hub",
     "https://www.doi.gov/tribalconsultation"),
    ("DOI",   "Department of the Interior", "policy",
     "https://www.doi.gov/elips/browse"),
    ("IHS",   "Indian Health Service", "consultation_hub",
     "https://www.ihs.gov/odsct/"),
    ("IHS",   "Indian Health Service", "consultation_hub",
     "https://www.ihs.gov/newsroom/dear-tribal-leader-letters/"),
    ("IHS",   "Indian Health Service", "policy",
     "https://www.ihs.gov/consultation/"),
    ("EPA",   "Environmental Protection Agency", "consultation_hub",
     "https://www.epa.gov/tribal/tribal-consultation-opportunities-tracking-system"),
    ("EPA",   "Environmental Protection Agency", "consultation_hub",
     "https://tcots.epa.gov/"),
    ("EPA",   "Environmental Protection Agency", "policy",
     "https://www.epa.gov/tribal/epa-policy-consultation-and-coordination-indian-tribes"),
    ("HHS",   "Health and Human Services", "consultation_hub",
     "https://www.hhs.gov/about/agencies/iea/tribal-affairs/index.html"),
    ("HHS",   "Health and Human Services", "policy",
     "https://www.hhs.gov/about/agencies/iea/tribal-affairs/consultation/index.html"),
    ("USDA",  "Department of Agriculture", "consultation_hub",
     "https://www.usda.gov/about-usda/general-information/staff-offices/office-tribal-relations"),
    ("DOE",   "Department of Energy", "consultation_hub",
     "https://www.energy.gov/indianenergy/office-indian-energy-policy-and-programs"),
    ("DOE",   "Department of Energy", "policy",
     "https://www.energy.gov/management/doe-tribal-consultation-policy"),
    ("HUD",   "Housing and Urban Development", "consultation_hub",
     "https://www.hud.gov/program_offices/public_indian_housing/ih/codetalk"),
    ("DOT",   "Department of Transportation", "consultation_hub",
     "https://www.transportation.gov/tribal"),
    ("USACE", "Army Corps of Engineers", "consultation_hub",
     "https://www.usace.army.mil/Missions/Civil-Works/Tribal-Nations/"),
    ("FCC",   "Federal Communications Commission", "consultation_hub",
     "https://www.fcc.gov/consumer-governmental-affairs/office-native-affairs-and-policy"),
    ("NPS",   "National Park Service", "consultation_hub",
     "https://www.nps.gov/subjects/tribes/index.htm"),
    ("BLM",   "Bureau of Land Management", "consultation_hub",
     "https://www.blm.gov/programs/cultural-heritage-and-paleontology/tribal-consultation"),
    ("FWS",   "Fish and Wildlife Service", "consultation_hub",
     "https://www.fws.gov/native-american"),
    ("FWS",   "Fish and Wildlife Service", "policy",
     "https://www.fws.gov/policy-library/510fw1"),
]

# Phrases that constitute a PUBLISHED OBLIGATION - a required frequency or a
# named trigger. Like a compact's reporting clause, a published obligation is a
# map to records nobody has pulled.
#
# The phrasing agencies actually use is "we will consult with Tribal
# governments when ..." and "federal agencies are required to consult with
# Tribal Nations when projects may affect historic properties" - an obligation
# expressed as a verb with a trigger clause, not as the noun "consultation is
# required". A regex written for the latter matches nothing on any of the nine
# retrievable pages, which would have been recorded as "no obligation
# published" - a false negative about the most consequential field here.
FREQ_RE = re.compile(
    r"([^.]{0,170}(?:at least\s+)?(?:annual|annually|semi-?annual\w*|quarterly|"
    r"biannual\w*|twice (?:a|per) year|once (?:a|per) year|monthly|"
    r"every \w+ years?)[^.]{0,90}consult[^.]{0,170}\.|"
    r"[^.]{0,170}consult[^.]{0,130}(?:at least\s+)?(?:annually|quarterly|"
    r"semi-?annually|twice (?:a|per) year|once (?:a|per) year|"
    r"on an annual basis|each (?:fiscal )?year)[^.]{0,130}\.)", re.I)
TRIGGER_RE = re.compile(
    r"([^.]{0,210}(?:required to consult|must consult|shall consult|"
    r"will consult|are to consult|obligated to consult|"
    r"consultation (?:is|are|shall be|must be|will be) "
    r"(?:required|initiated|conducted))[^.]{0,250}\.)", re.I)


def html_to_text(body):
    """HTML -> text, preferring <main> but never trusting it blindly.

    Several agency templates put the substantive content OUTSIDE <main>, so a
    <main>-only reader returns 114 characters from a full page and the coverage
    file would then record a live page as near-empty. Fall back to the whole
    body whenever <main> yields implausibly little.
    """
    t = body.decode("utf-8", "replace")

    def strip(b):
        b = re.sub(r"<(script|style|nav|footer|header|svg|noscript)\b.*?</\1>",
                   " ", b, flags=re.S | re.I)
        b = re.sub(r"<!--.*?-->", " ", b, flags=re.S)
        b = re.sub(r"<[^>]+>", "\n", b)
        import html as _h
        s = _h.unescape(b)
        return "\n".join(x.strip() for x in s.split("\n") if x.strip())

    m = re.search(r"<main.*?</main>", t, re.S | re.I)
    out = strip(m.group(0)) if m else ""
    if len(out) < 800:
        full = strip(t)
        if len(full) > len(out):
            out = full
    return out


def stage_agencies():
    print("=== 96 stage AGENCIES: consultation pages, policies, reports ===\n")
    RAW.mkdir(parents=True, exist_ok=True)
    outdir = RAW / "agency_pages"
    outdir.mkdir(parents=True, exist_ok=True)

    claimed, probes = set(), []
    for key, label, kind, url in AGENCY_PAGES:
        host = urllib.parse.urlparse(url).netloc
        if host not in claimed:
            if not claim_host(host, "code/96_build_consultation_events.py",
                              "consultation policy/hub page probe (<=3 requests)"):
                probes.append({"agency_key": key, "agency": label, "kind": kind,
                               "url": url, "http_status": "",
                               "probe_result": "HOST_LOCKED_BY_ANOTHER_POLLER",
                               "fetched_date": TODAY})
                continue
            claimed.add(host)
        st, body = fetch(url, min_gap=1.5, timeout=60)
        fn = re.sub(r"[^a-z0-9]+", "_", f"{key}_{kind}_{host}".lower())[:120]
        text = ""
        if st == 200 and body:
            (outdir / f"{fn}.html").write_bytes(body)
            text = html_to_text(body)
            (outdir / f"{fn}.txt").write_text(text, encoding="utf-8")
        probes.append({
            "agency_key": key, "agency": label, "kind": kind, "url": url,
            "http_status": st,
            "probe_result": "OK" if st == 200 else
                            ("NOT_FOUND" if st == 404 else
                             ("BLOCKED_OR_UNREACHABLE" if st == 0 else f"HTTP_{st}")),
            "chars": len(text), "fetched_date": TODAY,
        })
        print(f"  {key:6s} {kind:16s} HTTP {st:3d}  {len(text):7,d} chars  {url}")

    # MERGE, never overwrite: a URL that 404'd on an earlier candidate slug is
    # evidence about our own guess and stays in the record. AGENTS.md: the BIA
    # Southwest Region page 404s at the obvious slug and lives elsewhere, so a
    # 404 must always be readable as "we asked wrongly", not "nothing is there".
    prior = read_csv(RAW / "agency_probe_log.csv")
    now = {p["url"] for p in probes}
    merged = probes + [p for p in prior if p["url"] not in now]
    merged.sort(key=lambda p: (p["agency_key"], p["kind"], p["url"]))
    write_csv(RAW / "agency_probe_log.csv", merged,
              ["agency_key", "agency", "kind", "url", "http_status",
               "probe_result", "chars", "fetched_date"])
    for h in claimed:
        release_host(h, "code/96_build_consultation_events.py",
                     "Consultation policy probe complete (<=3 requests). Released.")
    save_manifest()


# ===========================================================================
# STAGE 3 - PARSE
# ===========================================================================

# ---- 3a. text normalisation ----------------------------------------------
# The GPO text is hard-wrapped at ~72 columns and carries page-break furniture.
PAGEBREAK_RE = re.compile(r"\[\[Page[^\]]*\]\]")
BULLET_RE = re.compile(r"<bullet>")
TAGS_RE = re.compile(r"<[^>]+>")


def flatten(raw):
    t = raw
    t = re.sub(r"<html>.*?<pre>", "", t, flags=re.S | re.I)
    t = TAGS_RE.sub(" ", t)
    import html as _h
    t = _h.unescape(t)
    t = PAGEBREAK_RE.sub(" ", t)
    t = t.replace("``", '"').replace("''", '"')
    t = re.sub(r"[ \t]+", " ", t)
    # unwrap hard line breaks inside paragraphs, keep blank-line paragraphing
    t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def section(text, name, stop_words):
    """Return the named section body, or ''. Headings are bare title lines."""
    m = re.search(rf"(?:^|\s){re.escape(name)}\s+", text)
    if not m:
        return ""
    body = text[m.end():]
    stops = [body.find(s) for s in stop_words if body.find(s) > 0]
    return body[:min(stops)] if stops else body[:6000]


FIELD_RE = {
    "dates": re.compile(r"\bDATES?:\s*(.{0,1800}?)(?=\s(?:ADDRESSES|FOR FURTHER|"
                        r"SUPPLEMENTARY|SUMMARY|AGENCY):|$)", re.S),
    "addresses": re.compile(r"\bADDRESSES?:\s*(.{0,2500}?)(?=\s(?:FOR FURTHER|"
                            r"SUPPLEMENTARY|DATES|SUMMARY):|$)", re.S),
    "summary": re.compile(r"\bSUMMARY:\s*(.{0,2500}?)(?=\s(?:DATES|ADDRESSES|"
                          r"FOR FURTHER|SUPPLEMENTARY):|$)", re.S),
    "action": re.compile(r"\bACTION:\s*(.{0,300}?)(?=\s(?:SUMMARY|DATES):|$)", re.S),
}

CONSULT_STOPS = ["History and Description", "Determinations Made",
                 "Additional Requestors", "Disposition", "Abstract of Information",
                 "Cultural Affiliation", "Background and History",
                 "Description of the", "The National Park Service is not"]


# ---- 3b. role grammar -----------------------------------------------------
#
# FORWARD markers govern the names that FOLLOW them.
# BACKWARD markers govern the names that PRECEDE them, in the same sentence.
# A sentence containing NO marker yields NO participants. This is the guard
# that keeps "invited" from silently becoming "attended".

FORWARD_MARKERS = [
    (re.compile(r"in consultation with (?:representatives of )?(?:the )?", re.I),
     "consulted"),
    (re.compile(r"consultation (?:was|were|has been|have been) (?:held|conducted|"
                r"initiated|undertaken) with (?:representatives of )?(?:the )?", re.I),
     "consulted"),
    (re.compile(r"(?:staff |officials )?consulted with (?:representatives of )?(?:the )?", re.I),
     "consulted"),
    (re.compile(r"(?:the following .{0,60}?)?(?:were|was) consulted:?\s*", re.I),
     "consulted"),
    (re.compile(r"participated in (?:the )?consultation:?\s*", re.I),
     "consulted"),
    (re.compile(r"(?:were|was) invited to (?:consult|participate in consultation):?\s*", re.I),
     "invited"),
    (re.compile(r"(?:has|have) (?:been )?requested (?:the )?repatriation .{0,80}?by (?:the )?", re.I),
     "requested_repatriation"),
    (re.compile(r"repatriation .{0,60}?requested by (?:the )?", re.I),
     "requested_repatriation"),
    (re.compile(r"submitted (?:written )?comments:?\s*", re.I),
     "submitted_comment"),
    (re.compile(r"co-?hosted (?:by|with) (?:the )?", re.I), "co_hosted"),
]

BACKWARD_MARKERS = [
    (re.compile(r"(?:were|was) (?:contacted|invited|notified)[^.;]{0,80}?"
                r"(?:but )?did not (?:attend|participate|respond|reply)", re.I),
     "invited_did_not_participate"),
    (re.compile(r"did not (?:attend|participate in|respond to)[^.]{0,60}?consultation", re.I),
     "invited_did_not_participate"),
    (re.compile(r"(?:were|was) (?:contacted|invited|notified) for consultation", re.I),
     "invited"),
    (re.compile(r"(?:were|was) invited to (?:consult|participate)", re.I), "invited"),
    (re.compile(r"(?:were|was) consulted", re.I), "consulted"),
    (re.compile(r"participated in (?:the )?consultation", re.I), "consulted"),
    (re.compile(r"(?:attended|took part in) the consultation", re.I), "attended"),
    (re.compile(r"submitted (?:written )?comments", re.I), "submitted_comment"),
]

# Never split a sentence on these: they end in a period but not a sentence.
# "Sault Ste. Marie Tribe of Chippewa Indians" and "St. Regis Mohawk Tribe" are
# tribe names with a period inside them, so a naive split shatters a name and
# hands the resolver a fragment - and a fragment is what a false match feeds on.
ABBREV = {
    "st", "ste", "mt", "mts", "ft", "dr", "mr", "mrs", "ms", "jr", "sr",
    "inc", "co", "corp", "ltd", "no", "nos", "ave", "rd", "blvd", "apt",
    "u.s", "n.m", "n.c", "n.d", "s.d", "n.y", "d.c", "wash", "ariz", "calif",
    "colo", "okla", "wis", "minn", "mich", "nev", "neb", "nebr", "mont",
    "wyo", "oreg", "tenn", "fla", "ga", "ala", "ky", "va", "md", "del",
    "ill", "ind", "kans", "la", "mass", "miss", "mo", "pa", "vt", "conn",
    "approx", "e.g", "i.e", "cf", "vs", "al", "ph", "d",
}
_SENT_CAND_RE = re.compile(r"\.\s+(?=[\"A-Z0-9])")
_LASTWORD_RE = re.compile(r"([A-Za-z][A-Za-z.]*)$")


def sentences(text):
    """Split into sentences, refusing to split after a known abbreviation.

    Python's `re` has no variable-width look-behind, so the abbreviation guard
    is applied by inspecting the token immediately before each candidate break
    rather than by encoding it in the pattern.
    """
    out, start = [], 0
    for m in _SENT_CAND_RE.finditer(text):
        w = _LASTWORD_RE.search(text[max(0, m.start() - 24):m.start()])
        if w and w.group(1).lower().rstrip(".") in ABBREV:
            continue
        seg = text[start:m.start() + 1].strip()
        if seg:
            out.append(seg)
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


BRACKET_RE = re.compile(r"\[[^\]]*\]")
# "(previously listed as Oneida Tribe of Indians of Wisconsin)" is NOT noise -
# it is the Federal Register disambiguating two tribes that share a name, and
# it usually carries the state. Stripping it before resolution is what sent a
# Wisconsin consultation to the New York nation on 2026-08-07. It is retained
# here and consumed by the resolver.
# "<Umbrella> (<Band>; <Band>; ...)" - the Federal Register's way of naming
# which constituent bands of a federated tribe were involved.
CONSTITUENT_PAREN_RE = re.compile(r"^(?P<head>[^(]+?)\s*\((?P<inner>.+)\)\s*$",
                                  re.S)
FORMER_NAME_RE = re.compile(
    r"\((?:previously|formerly)\s+(?:listed\s+as\s+|known\s+as\s+|called\s+)?"
    r"([^)]+)\)", re.I)
# Leading connectives. "In addition, the Mashpee Wampanoag Tribe" resolved
# ambiguously ONLY because "In addition, the" was still glued to the name.
LEAD_STRIP_RE = re.compile(
    r"^(?:in addition|additionally|also|finally|further|furthermore|moreover|"
    r"lastly|however|and|the|&)\s*[,:]?\s+", re.I)
TRAIL_STRIP_RE = re.compile(r"[,;:.\s]+$")


def mask_parens(seg):
    """Protect semicolons INSIDE parentheses before splitting on semicolons.

    The Federal Register writes constituent bands inside a parenthetical using
    the SAME separator as the outer list:

        "Minnesota Chippewa Tribe, Minnesota (Bois Forte Band (Nett Lake);
         Fond du Lac Band; Grand Portage Band; Leech Lake Band; Mille Lacs
         Band; and White Earth Band)"

    That is ONE consulting government with its six constituent bands glossed,
    not six participants - and an unmasked split shatters it into six
    fragments, one of which is the string "White Earth Band)". Cedar has been
    bitten by a separator assumption before (the term-67 semicolon bug), so the
    parenthetical is masked, split, then restored.
    """
    out, depth = [], 0
    for ch in seg:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        out.append("\x00" if (ch == ";" and depth > 0) else ch)
    return "".join(out)


def split_names(seg):
    """Semicolon-delimited official tribe names -> individual names.

    Commas are NOT separators: the official Federal Register names carry them
    ("Ute Mountain Tribe of the Ute Mountain Reservation, Colorado, New Mexico
    & Utah"). Splitting on commas shatters every multi-state name into
    fragments, and fragments are what feed a false match.
    """
    seg = BRACKET_RE.sub(" ", seg)
    seg = re.sub(r"\s+", " ", seg).strip()
    # " and the " JOINS TWO ORGANISATIONS and must be treated as a separator.
    # "Red Lake Band of Chippewa Indians, Minnesota and the Turtle Mountain
    # Band ..." is two tribes; kept whole, the head rule captures Red Lake and
    # silently drops Turtle Mountain. Worse, "Haudenosaunee Standing Committee
    # on Burial Rules and Regulations and the Oneida Indian Nation" resolved
    # ENTIRELY to the Oneida Indian Nation.
    #
    # The narrow form " and the " is safe: the official names that contain
    # "and" bind it to a bare noun, not to a determiner - "Assiniboine AND
    # SIOUX Tribes", "Cheyenne AND ARAPAHO Tribes", "Confederated Tribes AND
    # BANDS of the Yakama Nation", "Sac AND FOX Nation". None of them contains
    # " and the ".
    masked = re.sub(
        r",?\s+and\s+(?:(?:representatives|representative|officials|official|"
        r"members|member|delegates|leaders|staff)\s+of\s+)?the\s+",
        ";the ", mask_parens(seg))
    parts = masked.split(";")
    out = []
    for p in parts:
        p = p.replace("\x00", ";")
        p = TRAIL_STRIP_RE.sub("", LEAD_STRIP_RE.sub("", p.strip()))
        p = TRAIL_STRIP_RE.sub("", LEAD_STRIP_RE.sub("", p.strip()))
        if 3 < len(p) <= 220:
            out.append(p)
    return out


ENTITY_WORDS_RE = re.compile(
    r"\b(tribe|tribes|tribal|nation|nations|band|bands|pueblo|rancheria|"
    r"village|community|colony|reservation|indians|nsn|native hawaiian|"
    r"organization|corporation|council|confederated|of oklahoma|of california)\b",
    re.I)


# Prose, not a name. These fragments reached the resolver because they contain
# the word "tribes" or "governments": "Ninety percent of tribal governments
# who...", "In addition, written comments were received from 14 tribes,...",
# "State, local, and tribal governments, the intergovernmental...". None is an
# entity, and every one of them is a chance for a containment match to invent
# a participant.
PROSE_RE = re.compile(
    r"\b(the following|percent|opportunity|written comments|received from|"
    r"were included|are included|such as|other parties|in the process|"
    r"development of|proposed regul|representatives and|intergovernmental|"
    r"as well as|among others|includ(?:e|es|ing)|consist(?:s|ing)?|"
    r"pursuant to|in accordance|believes? itself|may contact|should contact)\b",
    re.I)
NOT_A_NAME_RE = re.compile(
    r"\b(museum|universit|college|societ|department|bureau|"
    r"service|institute|association of|state of|county|city of|"
    r"office of|division of|national park|monument|laborator|hospital|"
    r"historical societ|foundation|archaeolog|anthropolog)\b", re.I)


def looks_like_entity(name):
    """A participant name must look like a governmental/organisational name.

    Without this, a sentence tail like "the museum" or a person's name enters
    the resolver, and the resolver's containment tier will eventually find
    SOMETHING for it. Attendee lists are trap-dense; the cheapest defence is
    refusing to ask the question about a string that is not a name.
    """
    if not ENTITY_WORDS_RE.search(name):
        return False
    if NOT_A_NAME_RE.search(name):
        return False
    if PROSE_RE.search(name):
        return False
    if re.match(r"^(?:mr|ms|mrs|dr)\b", name, re.I):
        return False
    # A name starts like a name: a capital letter or a digit-led band number.
    if not re.match(r"^[A-Z0-9\"']", name):
        return False
    # Real official names run long, but not sentence-long.
    if len(name.split()) > 26:
        return False
    return True


def harvest_participants(consult_text):
    """-> [(name, role, source_quote)] with role from the SAME sentence.

    Role is never inferred across a sentence boundary, and never upgraded.
    """
    out = []
    for sent in sentences(consult_text):
        if len(sent) > 6000:
            continue
        fwd = [(m.start(), m.end(), role) for rx, role in FORWARD_MARKERS
               for m in [rx.search(sent)] if m]
        bwd = [(m.start(), m.end(), role) for rx, role in BACKWARD_MARKERS
               for m in [rx.search(sent)] if m]
        if not fwd and not bwd:
            continue                      # no role marker -> no participants
        quote = sent if len(sent) <= 900 else sent[:900] + "..."

        if bwd:
            # names PRECEDE the earliest backward marker in this sentence
            s, _, role = min(bwd, key=lambda x: x[0])
            seg = sent[:s]
            if fwd:                       # forward marker also present: names
                fs, fe, frole = min(fwd, key=lambda x: x[0])
                if fe <= s:
                    seg = sent[fe:s]
                    # the forward marker's own names are the same span; the
                    # backward verb is what the sentence ASSERTS about them.
            for nm in split_names(seg):
                if looks_like_entity(nm):
                    out.append((nm, role, quote))
            continue

        s, e, role = min(fwd, key=lambda x: x[0])
        for nm in split_names(sent[e:]):
            if looks_like_entity(nm):
                out.append((nm, role, quote))
    return out


# ---- 3c. dates, location, format -----------------------------------------

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], 1)}
MONTH_ALT = "|".join(list(MONTHS) + [m[:3] for m in MONTHS])
DATE_RE = re.compile(rf"\b({MONTH_ALT})\.?\s+(\d{{1,2}})(?:\s*,)?\s*(\d{{4}})\b", re.I)
DATE_NOYEAR_RE = re.compile(rf"\b({MONTH_ALT})\.?\s+(\d{{1,2}})\b", re.I)

MEETING_WORDS_RE = re.compile(
    r"\b(meeting|session|consultation will|will be held|will convene|webinar|"
    r"teleconference|conference call|listening session|will conduct|hearing)\b",
    re.I)
COMMENT_WORDS_RE = re.compile(
    r"\b(comments? (?:must|should|are due|will be accepted|may be submitted)|"
    r"written comments|submit comments|comment period|received (?:on or )?"
    r"(?:before|by))\b", re.I)


def iso_dates(text, fallback_year=None):
    out = []
    for m in DATE_RE.finditer(text):
        mo, d, y = MONTHS[m.group(1).lower()[:3] if len(m.group(1)) == 3
                          else m.group(1).lower()], int(m.group(2)), int(m.group(3))
        if 1 <= d <= 31 and 1990 <= y <= 2035:
            out.append(f"{y:04d}-{mo:02d}-{d:02d}")
    if not out and fallback_year:
        for m in DATE_NOYEAR_RE.finditer(text):
            key = m.group(1).lower()
            mo = MONTHS.get(key) or MONTHS.get(
                next((k for k in MONTHS if k.startswith(key[:3])), ""), None)
            d = int(m.group(2))
            if mo and 1 <= d <= 31:
                out.append(f"{int(fallback_year):04d}-{mo:02d}-{d:02d}")
    return sorted(set(out))


def month_key(name):
    n = name.lower()
    return MONTHS.get(n) or MONTHS.get(
        next((k for k in MONTHS if k.startswith(n[:3])), ""), None)


FORMAT_PATTERNS = [
    (re.compile(r"\bvirtual|\bwebinar|\bzoom\b|\bwebex\b|\bmicrosoft teams\b", re.I), "virtual"),
    (re.compile(r"\bteleconference|\bconference call|\btoll-?free (?:number|call)", re.I), "teleconference"),
    (re.compile(r"\bin[- ]person\b", re.I), "in_person"),
    (re.compile(r"\bwritten comment", re.I), "written_comment"),
]

TYPE_PATTERNS = [
    (re.compile(r"native american graves protection|NAGPRA", re.I), "NAGPRA"),
    (re.compile(r"negotiated rulemaking", re.I), "negotiated_rulemaking"),
    (re.compile(r"dear tribal leader", re.I), "dear_tribal_leader_letter"),
    (re.compile(r"listening session", re.I), "listening_session"),
    (re.compile(r"tribal consultation (?:session|meeting)s?", re.I), "consultation_session"),
    (re.compile(r"section 106|national historic preservation act", re.I), "NHPA_section_106"),
    (re.compile(r"\bsummit\b", re.I), "tribal_summit"),
    (re.compile(r"\bbudget (?:formulation|consultation)", re.I), "budget_consultation"),
    (re.compile(r"\btribal (?:advisory|self-governance) committee", re.I), "advisory_committee"),
]

LOC_RE = re.compile(
    r"\b([A-Z][A-Za-z.'\- ]{2,28}?),\s*(Alabama|Alaska|Arizona|Arkansas|California|"
    r"Colorado|Connecticut|Delaware|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|"
    r"Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|"
    r"Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|"
    r"New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|"
    r"Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|"
    r"Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|"
    r"District of Columbia|D\.C\.|AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|"
    r"KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|"
    r"SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b")

STATE_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}


def states_in(name):
    """State postal codes named inside a record's own name."""
    out = set()
    low = name.lower()
    for full, ab in STATE_ABBR.items():
        if re.search(rf"\b{re.escape(full)}\b", low):
            out.add(ab)
    for m in re.finditer(r"\b([A-Z]{2})\b", name):
        if m.group(1) in set(STATE_ABBR.values()):
            out.add(m.group(1))
    return out


# ---- 3d. guarded resolution ----------------------------------------------

GOVERNMENT_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
    "Native Hawaiian Organization",       # NAGPRA names NHOs as consulting parties
    "Federal-level self-governance consortium",
    "Intertribal Organization",
    # CONSTITUENT BANDS ARE GOVERNMENTS AND CONSULT IN THEIR OWN RIGHT.
    # The Leech Lake, Mille Lacs, Bois Forte, Fond du Lac, Grand Portage and
    # White Earth Bands each appear by name in Federal Register consultation
    # records; so do the Te-Moak and Fort Hall bands. Excluding this class sent
    # ~85 correctly-named participants to review for no reason.
    #
    # This is a PARTICIPATION judgment, not a money judgment. AGENTS.md's rule
    # that "a constituent band's contracts are not the umbrella's" is about
    # roll-up, and nothing here rolls up: a consultation row names the band
    # that consulted and never credits the umbrella tribe with it.
    "Federal-level constituency entity",
}


class Resolver:
    """resolve_entity, wrapped in the guards the containment defect requires."""

    def __init__(self, spine):
        self.spine = spine
        self.gov = [r for r in spine if r["entity_class"] in GOVERNMENT_CLASSES]
        self.by_fr = {}
        for r in spine:
            fr = (r.get("fr_official_name") or "").strip()
            if fr:
                self.by_fr.setdefault(norm(fr), r)
        self.by_canon = {}
        for r in self.gov:
            self.by_canon.setdefault(norm(r["canonical_name"]), r)
        self.cache = {}
        # Spine IDs encode the family in their middle token: the Minnesota
        # Chippewa umbrella is TRBF-MINNCH-00 and its six bands are
        # CNSF-MINNCH-BF/FL/GP/LL/ML/WE. Same for TEMOAK and FTHALL. That token
        # is what lets a parenthetical band list be matched against the RIGHT
        # bands rather than against every band in the country.
        self.family = defaultdict(list)
        for r in self.gov:
            parts = r["tribe_id"].split("-")
            if len(parts) >= 2:
                self.family[parts[1]].append(r)

    def resolve(self, name):
        """-> (tribe_id, canonical, method, reason)."""
        if name in self.cache:
            return self.cache[name]
        res = self._resolve_pair(name)
        self.cache[name] = res
        return res

    def _resolve_pair(self, name):
        """Resolve a published name that may carry its own former name.

        The Federal Register writes "Oneida Nation (previously listed as Oneida
        Tribe of Indians of Wisconsin)". Both halves name the SAME sovereign,
        and the parenthetical is usually the only thing distinguishing it from
        a same-named tribe in another state. So:

          * states are read from the WHOLE string, both halves;
          * both halves are resolved;
          * if they resolve to DIFFERENT entities the record is
            self-contradictory and neither is used.

        Refusing a contradiction is the entire point. Picking the half that
        happens to match is how the New York and Wisconsin Oneida nations get
        confused, and they are two distinct federally recognised nations
        (cedar_domain.STANDING_DISAMBIGUATIONS).
        """
        m = FORMER_NAME_RE.search(name)
        former = m.group(1).strip() if m else ""
        current = re.sub(r"\s+", " ", FORMER_NAME_RE.sub(" ", name)).strip()
        current = TRAIL_STRIP_RE.sub("", current) or name
        st = states_in(name)

        a = self._resolve(current, st)
        if not former:
            return a
        b = self._resolve(former, st)
        if a[0] and b[0] and a[0] != b[0]:
            return None, None, "", (f"current_vs_former_name_disagree:"
                                    f"{a[1]}|{b[1]}")
        if a[0]:
            return a
        if b[0]:
            return b[0], b[1], b[2] + "_via_former_name", ""
        return a if a[3] else b

    def expand_constituents(self, name):
        """"<Umbrella> (<Band>; <Band>; ...)" -> one row PER BAND, or None.

        THE FACT THIS PRESERVES
        -----------------------
        87 FR 65120 (2022-22514) lists, in the SAME notice:

            consulted:  "... Minnesota Chippewa Tribe, Minnesota (Mille Lacs
                        Band); ..."
            invited but did not participate:
                        "... Minnesota Chippewa Tribe, Minnesota (Bois Forte
                        Band (Nett Lake); Fond du Lac Band; Grand Portage Band;
                        Leech Lake Band; White Earth Band); ..."

        The parenthetical is not decoration - it names WHICH BANDS did each
        thing. Collapsing both strings to the umbrella tribe makes one tribe
        simultaneously present and absent from the same consultation, which is
        not a fact about the world but an artefact of dropping the qualifier.

        Expansion is ALL-OR-NOTHING: if any listed band fails to resolve within
        the umbrella's own family, the whole expansion is refused and the
        caller falls back to the umbrella. A partial expansion would silently
        drop the bands that did not match, which is the same class of error as
        the one being fixed.
        """
        m = CONSTITUENT_PAREN_RE.match((name or "").strip())
        if not m:
            return None
        inner = m.group("inner")
        # "(previously listed as ...)" is a former name, not a band list.
        if re.match(r"\s*(?:previously|formerly|hereinafter|hereafter)\b",
                    inner, re.I):
            return None
        head = m.group("head").strip()
        hid, hcanon, hmethod, _ = self._resolve_pair(head)
        if not hid or "-" not in hid:
            return None
        kin = [r for r in self.family.get(hid.split("-")[1], [])
               if r["tribe_id"] != hid
               and r["entity_class"] == "Federal-level constituency entity"]
        if not kin:
            return None

        items = [x.replace("\x00", ";").strip()
                 for x in mask_parens(inner).split(";")]
        items = [TRAIL_STRIP_RE.sub("", LEAD_STRIP_RE.sub("", x)).strip()
                 for x in items if x.strip()]
        if not items:
            return None

        out = []
        for it in items:
            c = core(it)
            if not c:
                return None
            exact = [r for r in kin if core(r["canonical_name"]) == c]
            if len(exact) == 1:
                pick = exact
            else:
                pick = [r for r in kin
                        if core(r["canonical_name"])
                        and core(r["canonical_name"]) <= c
                        and norm(it).startswith(norm(r["canonical_name"]))]
            if len({r["tribe_id"] for r in pick}) != 1:
                return None
            r = pick[0]
            out.append((f"{head} ({it})", r["tribe_id"], r["canonical_name"],
                        "constituent_band_in_parenthetical"))
        return out

    def _resolve(self, name, rec_states=None):
        n = norm(name)
        if rec_states is None:
            rec_states = states_in(name)

        # TIER 1 - the record's own name IS the Federal Register official name.
        # This is the whole reason NAGPRA notices resolve cleanly, and it needs
        # no containment at all.
        r = self.by_fr.get(n)
        if r:
            return r["tribe_id"], r["canonical_name"], "fr_official_name", ""
        c = core(name)

        # THE TRAP GUARD, applied at EVERY tier below tier 1.
        #
        # A tier-1 hit on `fr_official_name` is safe even for a trap token,
        # because the Federal Register's official names are unique by
        # construction. Every weaker tier is not. "Oneida Nation" has exactly
        # one identifying token and it is in NAME_TRAPS, and there are two
        # federally recognised Oneida nations - so any tier that would answer
        # it is guessing between two sovereigns.
        trap_only = bool(c) and c <= set(NAME_TRAPS)

        def state_ok(row):
            sp = (row.get("state") or "").strip().upper()
            return not (rec_states and sp and sp not in rec_states)

        def state_corroborates(row):
            """The record NAMES a state and the entity IS in it.

            This is a second, independent leg of evidence, and it is what
            rescues a legitimate trap-token name: "Oneida Nation of New York"
            shares only the trapped token `oneida` with spine "Oneida", but the
            record says New York and the entity is in New York. Two Oneida
            nations exist and this picks the right one on evidence rather than
            on luck. Absent that corroboration the trap guard still refuses.
            """
            sp = (row.get("state") or "").strip().upper()
            return bool(rec_states and sp and sp in rec_states)

        def trap_blocks(row):
            return trap_only and not state_corroborates(row)

        r = self.by_canon.get(n)
        if r and not trap_blocks(r) and state_ok(r):
            return r["tribe_id"], r["canonical_name"], "exact_canonical", ""

        # TIER 2 - fr_official_name is a PREFIX of the record's name, or the
        # record is a prefix of it. Official names gained and lost state
        # suffixes over 30 years ("Pueblo of Zia" / "Zia Pueblo, New Mexico").
        # ONE DIRECTION ONLY. `fr.startswith(n)` - the entity's official name
        # being LONGER than the record - is the unsafe direction, and it fired:
        # the spine's Fond du Lac row carries fr_official_name "Minnesota
        # Chippewa Tribe, Minnesota (Six component reservations...)", so the
        # record "Minnesota Chippewa Tribe, Minnesota" - the UMBRELLA - matched
        # a single one of its six bands. A record less specific than the entity
        # is never enough to pick that entity.
        cands = []
        for r in self.gov:
            fr = norm(r.get("fr_official_name") or "")
            if fr and n.startswith(fr + " "):
                cands.append(r)
        cands = [r for r in cands if state_ok(r)]
        ids = {r["tribe_id"] for r in cands}
        if len(ids) == 1 and not trap_blocks(cands[0]):
            r = cands[0]
            return r["tribe_id"], r["canonical_name"], "fr_official_prefix", ""
        if len(ids) > 1:
            return None, None, "", ("ambiguous_fr_prefix:" +
                                    ",".join(sorted({c2["canonical_name"] for c2 in cands})[:4]))

        # TIER 2b - core-set equality RESTRICTED TO GOVERNMENT CLASSES.
        #
        # "Native Village of Afognak" is ambiguous against the full spine
        # because Afognak Native Corporation shares its identifying token - the
        # exact Alaska trap AGENTS.md records ("containment rewards the
        # SHORTEST spine name, and in Alaska that is usually the ANCSA
        # corporation"). But a party consulted under NAGPRA is a GOVERNMENT,
        # and among governments the name is unique. Restricting the class first
        # is what makes the answer safe, not a tie-break afterwards.
        if c:
            hits = [r for r in self.gov
                    if core(r["canonical_name"]) == c and state_ok(r)]
            if len({r["tribe_id"] for r in hits}) == 1 and not trap_blocks(hits[0]):
                r = hits[0]
                return r["tribe_id"], r["canonical_name"], "government_class_core", ""

        # TIER 2c - THE HEAD RULE.
        #
        # An official Native government name LEADS with the entity and then
        # qualifies it: "Leech Lake Band OF THE Minnesota Chippewa Tribe,
        # Minnesota"; "Minnesota Chippewa Tribe, Minnesota (Fond du Lac Band;
        # Mille Lacs Band; ...)". The head is the entity; everything after is
        # qualification, enumeration, or a state.
        #
        # Matching on token overlap instead gets both of those wrong - it
        # scores the six enumerated bands higher than the umbrella that
        # actually leads the string, and it let a "Haudenosaunee Standing
        # Committee..." segment resolve to the Oneida Indian Nation on the
        # strength of a name appearing far later in the sentence.
        heads = []
        for r in self.gov:
            for nm2 in (r["canonical_name"], r.get("fr_official_name") or ""):
                h = norm(nm2)
                if h and (n == h or n.startswith(h + " ")):
                    heads.append((len(h), r))
        if heads:
            best = max(h[0] for h in heads)
            top = [r for ln, r in heads if ln == best and state_ok(r)]
            ids = {r["tribe_id"] for r in top}
            if len(ids) == 1 and not trap_blocks(top[0]):
                r = top[0]
                return r["tribe_id"], r["canonical_name"], "name_head", ""
            if len(ids) > 1:
                return None, None, "", ("ambiguous_name_head:" + ",".join(
                    sorted({r["canonical_name"] for r in top})[:4]))

        # TIER 3 - the ONE resolver. Its result is then re-audited below.
        tid, canon, how = resolve_entity(name, self.spine)
        if not tid:
            return None, None, "", how

        row = next((r for r in self.spine if r["tribe_id"] == tid), None)
        if row is None:
            return None, None, "", "spine_row_missing"

        # GUARD 1 - class. A consultation participant is a sovereign or a
        # Native Hawaiian organisation, never a school, a CDFI or a college.
        if row["entity_class"] not in GOVERNMENT_CLASSES:
            return None, None, "", f"non_government_class:{row['entity_class']}"

        if how in ("exact", "alias"):
            return tid, canon, f"resolve_entity_{how}", ""

        # GUARD 2 - SPECIFICITY. Containment (and set-equality reached through
        # a short spine name) is accepted ONLY when the record is at least as
        # specific as the entity. The entity-contains-record direction is the
        # one that put $2.8B on a school; it is refused outright here.
        rc, nc = core(row["canonical_name"]), c
        if not rc <= nc:
            return None, None, "", (f"record_less_specific_than_entity:"
                                    f"{row['canonical_name']}")

        # GUARD 3 - TRAP TOKENS. If everything the two names share is a known
        # trap word, the match rests on nothing.
        shared = rc & nc
        if (shared and shared <= set(NAME_TRAPS)
                and not state_corroborates(row)):
            return None, None, "", f"only_trap_tokens_shared:{sorted(shared)}"
        if not shared:
            return None, None, "", "no_shared_identifying_token"

        # GUARD 4 - STATE AGREEMENT, where both sides carry one. Cross-state is
        # how an NM cultural centre reached a HI learning centre. `rec_states`
        # is the caller's, so a state named only in the "(previously listed
        # as ...)" half still counts.
        sp_state = (row.get("state") or "").strip().upper()
        if rec_states and sp_state and sp_state not in rec_states:
            return None, None, "", (f"state_disagreement:record={sorted(rec_states)}"
                                    f" spine={sp_state}")

        # GUARD 5 - THE HEAD RULE, applied to whatever containment returned.
        # If the entity's name does not begin the record's name, the record is
        # not primarily about that entity. This is what stops a multi-entity
        # sentence fragment from resolving to whichever name it happens to
        # contain.
        if not (n == norm(row["canonical_name"])
                or n.startswith(norm(row["canonical_name"]) + " ")
                or (norm(row.get("fr_official_name") or "")
                    and n.startswith(norm(row["fr_official_name"]) + " "))):
            return None, None, "", ("entity_name_does_not_lead_record:"
                                    f"{row['canonical_name']}")

        return tid, canon, f"resolve_entity_{how}_guarded", ""


# ---- 3e. the build --------------------------------------------------------

def stage_build():
    print("=== 96 stage BUILD: consultation_events.csv ===\n")
    docs, notices, refd = fr_document_numbers()
    meta_path = RAW / "fr_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    print(f"documents in scope : {len(docs):,}")
    print(f"metadata on disk   : {len(meta):,}")
    have_text = {p.stem for p in FRTEXT.glob("*.txt")}
    print(f"full text on disk  : {len(have_text):,}\n")

    spine = read_csv(SPINE_DIR / "cedar_entity_spine.csv")
    R = Resolver(spine)
    print(f"spine: {len(spine):,} entities, "
          f"{len(R.gov):,} of a class that may be a consultation participant\n")

    rows, unresolved = [], []
    stats = Counter()
    notice_ids = {r["document_number"] for r in notices}

    for dn, kind in docs.items():
        m = meta.get(dn) or {}
        tp = FRTEXT / f"{dn}.txt"
        raw = tp.read_text(encoding="utf-8", errors="replace") if tp.exists() else ""
        text = flatten(raw) if raw else ""
        stats["documents_seen"] += 1
        if not text:
            stats["no_full_text"] += 1

        ags = m.get("agencies") or []
        parents = [a for a in ags if not a.get("parent_id")]
        children = [a for a in ags if a.get("parent_id")]
        agency = (parents[0]["name"] if parents else
                  (ags[0]["name"] if ags else ""))
        sub_agency = children[0]["name"] if children else ""
        pub = m.get("publication_date") or ""
        year = pub[:4] if pub else ""
        title = m.get("title") or ""
        html_url = m.get("html_url") or ""
        citation = m.get("citation") or ""
        abstract = m.get("abstract") or ""

        blob = f"{title} {abstract} {text[:20000]}"

        ctype = ""
        for rx, lab in TYPE_PATTERNS:
            if rx.search(blob):
                ctype = lab
                break
        if not ctype:
            ctype = "consultation_notice" if kind == "notice" else "consultation_reported"
        if kind == "referenced" and ctype == "NAGPRA":
            ctype = "NAGPRA_consultation_reported"

        dates_txt = ""
        mm = FIELD_RE["dates"].search(text)
        if mm:
            dates_txt = mm.group(1)[:1800]
        elif m.get("dates"):
            dates_txt = m["dates"]
        addr_txt = ""
        mm = FIELD_RE["addresses"].search(text)
        if mm:
            addr_txt = mm.group(1)[:2000]

        # ---- comment deadline: structured field first, never inferred ----
        deadline = (m.get("comments_close_on") or "") or ""
        if not deadline and dates_txt and COMMENT_WORDS_RE.search(dates_txt):
            for s in sentences(dates_txt):
                if COMMENT_WORDS_RE.search(s):
                    ds = iso_dates(s, year)
                    if ds:
                        deadline = ds[-1]
                        break

        # ---- event dates: ONLY from a sentence that talks about a meeting ---
        ev_start = ev_end = ""
        if dates_txt:
            md = []
            for s in sentences(dates_txt):
                if MEETING_WORDS_RE.search(s) and not COMMENT_WORDS_RE.search(s):
                    md += iso_dates(s, year)
            md = sorted(set(d for d in md if d != deadline))
            if md:
                ev_start, ev_end = md[0], md[-1]

        fmt = ";".join(lab for rx, lab in FORMAT_PATTERNS
                       if rx.search(dates_txt + " " + addr_txt + " " + abstract))

        loc = ""
        if addr_txt:
            hits = [f"{a.strip()}, {b}" for a, b in LOC_RE.findall(addr_txt)]
            loc = ";".join(dict.fromkeys(hits))[:300]

        program = ""
        mmm = re.search(r"^(.{0,120}?),\s*(?:has completed|has determined|"
                        r"in consultation with)", abstract)
        if mmm:
            program = mmm.group(1).strip()

        has_written = int(bool(re.search(r"written comment", blob, re.I)))
        has_summary = int(bool(re.search(r"consultation (?:summary|report)|"
                                         r"summary of (?:the )?consultation", blob, re.I)))
        has_transcript = int(bool(re.search(r"\btranscript\b", blob, re.I)))

        ev_id = f"CONS-FR-{dn}"
        base = {
            "consultation_event_id": ev_id,
            "channel": CHANNEL,
            "agency": agency,
            "sub_agency": sub_agency,
            "program": program,
            "consultation_type": ctype,
            "topic": title,
            "notice_date": pub,
            "event_start_date": ev_start,
            "event_end_date": ev_end,
            "location": loc,
            "format": fmt,
            "comment_deadline": deadline,
            "has_written_comments": has_written,
            "has_summary": has_summary,
            "has_transcript": has_transcript,
            "federal_register_citation": citation,
            "source_url": html_url or (m.get("raw_text_url") or ""),
            "fetched_date": TODAY,
            "built_date": TODAY,
        }

        # ---- participants -------------------------------------------------
        consult_sec = ""
        if text:
            consult_sec = section(text, "Consultation", CONSULT_STOPS)
            if not consult_sec:
                sup = re.search(r"SUPPLEMENTARY INFORMATION:\s*(.{0,20000})", text, re.S)
                consult_sec = sup.group(1) if sup else text[:20000]

        found = harvest_participants(consult_sec) if consult_sec else []
        # de-duplicate (name, role) within a document; keep the first quote
        seen_pr = {}
        for nm, role, q in found:
            seen_pr.setdefault((nm, role), q)

        # ---- resolve every (name, role), expanding band lists --------------
        resolved, failed = [], []
        for (nm, role), quote in sorted(seen_pr.items()):
            exp = R.expand_constituents(nm)
            if exp:
                for pub_nm, tid, canon, method in exp:
                    resolved.append((pub_nm, tid, canon, method, role, quote))
                continue
            tid, canon, method, reason = R.resolve(nm)
            if tid:
                resolved.append((nm, tid, canon, method, role, quote))
            else:
                failed.append((nm, role, quote, reason or "no_spine_match"))

        # ---- contradiction is a property of the ENTITY, not of the string ---
        #
        # Checking the published string missed the real case entirely: in
        # 2022-22514 the same tribe appeared as "Minnesota Chippewa Tribe,
        # Minnesota (Mille Lacs Band)" in the consulted list and as "Minnesota
        # Chippewa Tribe, Minnesota (Bois Forte Band; ... )" in the did-not-
        # participate list - two different strings, so a string-keyed check saw
        # no conflict while the output asserted a tribe was both present and
        # absent. After band expansion these are correctly six DIFFERENT
        # entities and no contradiction remains; where one genuinely does
        # remain, both rows go to review and neither is published.
        roles_by_entity = defaultdict(set)
        for _, tid, _, _, role, _ in resolved:
            roles_by_entity[tid].add(role)
        conflicted = {t for t, rs in roles_by_entity.items()
                      if "consulted" in rs and "invited_did_not_participate" in rs}

        emitted = 0
        for nm, role, quote, reason in failed:
            stats["participant_unresolved"] += 1
            unresolved.append({
                "consultation_event_id": ev_id, "agency": agency,
                "notice_date": pub, "participant_name_as_published": nm,
                "participant_role": role, "reason": reason,
                "source_url": html_url, "source_quote": quote[:600],
                "fetched_date": TODAY,
            })

        for nm, tid, canon, method, role, quote in resolved:
            if tid in conflicted:
                stats["participant_contradictory_role"] += 1
                unresolved.append({
                    "consultation_event_id": ev_id, "agency": agency,
                    "notice_date": pub, "participant_name_as_published": nm,
                    "participant_role": "|".join(sorted(roles_by_entity[tid])),
                    "reason": "contradictory_roles_for_same_entity_in_one_record",
                    "source_url": html_url, "source_quote": quote[:600],
                    "fetched_date": TODAY,
                })
                continue
            stats["participant_resolved"] += 1
            stats[f"role_{role}"] += 1
            r = dict(base)
            r.update({
                "tribe_id": tid, "tribe_name": canon,
                # The VERBATIM published string, kept beside our resolution of
                # it. Spec 3: "raw record -> source identity -> canonical
                # entity" must stay traceable, and without this column an
                # auditor cannot tell WHICH name in the quoted sentence became
                # this tribe_id.
                "participant_name_as_published": nm,
                "participant_role": role,
                "source_quote": quote[:900],
                # Tier A needs a human ruling or two independent legs. A single
                # published federal record, parsed, is one leg: tier B.
                "tier": Tier.B.value,
                "confidence": ("high" if method in
                               ("fr_official_name", "exact_canonical",
                                "fr_official_prefix", "name_head",
                                "constituent_band_in_parenthetical",
                                "resolve_entity_exact", "resolve_entity_alias")
                               else "medium"),
                "match_method": method,
            })
            rows.append(r)
            emitted += 1

        if not emitted:
            # THE EVENT IS STILL REAL. A consultation whose participants the
            # record does not enumerate is recorded with the participant fields
            # empty and the role stated as not_enumerated - never dropped, and
            # never expanded into "all 574 tribes".
            stats["events_without_named_participants"] += 1
            q = (abstract or title)[:900]
            r = dict(base)
            r.update({
                "tribe_id": "", "tribe_name": "",
                "participant_name_as_published": "",
                "participant_role": "not_enumerated",
                "source_quote": q,
                "tier": Tier.B.value, "confidence": "high",
                "match_method": "no_participants_named_in_record",
            })
            rows.append(r)

    # ---- output -----------------------------------------------------------
    FIELDS = ["consultation_event_id", "channel", "agency", "sub_agency",
              "program", "consultation_type", "topic", "notice_date",
              "event_start_date", "event_end_date", "location", "format",
              "tribe_id", "tribe_name", "participant_name_as_published",
              "participant_role", "comment_deadline",
              "has_written_comments", "has_summary", "has_transcript",
              "federal_register_citation", "source_url", "source_quote",
              "fetched_date", "tier", "confidence", "built_date",
              "match_method"]
    rows.sort(key=lambda r: (r["notice_date"], r["consultation_event_id"],
                             r["tribe_name"]))
    write_csv(CLEAN / "consultation_events.csv", rows, FIELDS)
    write_csv(REVIEW / f"consultation_unresolved_{TODAY}.csv", unresolved,
              ["consultation_event_id", "agency", "notice_date",
               "participant_name_as_published", "participant_role", "reason",
               "source_url", "source_quote", "fetched_date"])

    build_coverage(rows, docs, meta, have_text, notice_ids)
    report(rows, unresolved, stats)
    return rows, unresolved, stats


# ---- 3f. coverage: what each agency publishes, INCLUDING nothing ----------

def build_coverage(rows, docs, meta, have_text, notice_ids):
    probes = read_csv(RAW / "agency_probe_log.csv")
    by_agency = defaultdict(lambda: {"events": set(), "participants": 0,
                                     "tribes": set(), "years": set(),
                                     "with_summary": 0, "with_transcript": 0,
                                     "with_written": 0, "with_location": 0,
                                     "with_event_date": 0, "notices": set()})
    # THE OPERATIVE AGENCY IS THE SUB-AGENCY WHERE THERE IS ONE.
    #
    # Keying coverage on the parent department books all 1,829 NAGPRA notices
    # to "Interior Department" and then reports the National Park Service - the
    # agency that actually published every one of them - as publishing NOTHING.
    # That is precisely the false absence this file exists to prevent, so the
    # unit is the publishing agency and the department travels beside it.
    dept_of = {}
    for r in rows:
        a = r["sub_agency"] or r["agency"] or "(agency not stated in record)"
        dept_of.setdefault(a, r["agency"] or "")
        b = by_agency[a]
        b["events"].add(r["consultation_event_id"])
        if r["tribe_id"]:
            b["participants"] += 1
            b["tribes"].add(r["tribe_id"])
        if r["notice_date"]:
            b["years"].add(r["notice_date"][:4])
        b["with_summary"] += int(r["has_summary"] == 1)
        b["with_transcript"] += int(r["has_transcript"] == 1)
        b["with_written"] += int(r["has_written_comments"] == 1)
        b["with_location"] += int(bool(r["location"]))
        b["with_event_date"] += int(bool(r["event_start_date"]))

    # agency-page probes, keyed to a label
    probe_by_key = defaultdict(list)
    for p in probes:
        probe_by_key[p["agency_key"]].append(p)

    AGENCY_KEY_MAP = {
        "Interior Department": "DOI", "Indian Affairs Bureau": "BIA",
        "National Park Service": "NPS", "Land Management Bureau": "BLM",
        "Fish and Wildlife Service": "FWS",
        "Health and Human Services Department": "HHS",
        "Indian Health Service": "IHS",
        "Environmental Protection Agency": "EPA",
        "Agriculture Department": "USDA", "Energy Department": "DOE",
        "Housing and Urban Development Department": "HUD",
        "Transportation Department": "DOT",
        "Engineers Corps": "USACE", "Defense Department": "USACE",
        "Bureau of Indian Affairs": "BIA", "Indian Affairs Office": "BIA",
        "Reclamation Bureau": "DOI", "Forest Service": "USDA",
        "Federal Highway Administration": "DOT",
        "Centers for Disease Control and Prevention": "HHS",
        "Children and Families Administration": "HHS",
        "Centers for Medicare & Medicaid Services": "HHS",
        "Federal Communications Commission": "FCC",
    }

    out = []
    covered_keys = set()
    for a, b in sorted(by_agency.items()):
        key = AGENCY_KEY_MAP.get(a, "")
        covered_keys.add(key)
        pr = probe_by_key.get(key, [])
        yrs = sorted(b["years"])
        out.append({
            "agency": a, "parent_department": dept_of.get(a, ""),
            "agency_key": key,
            "n_consultation_events": len(b["events"]),
            "n_participant_rows": b["participants"],
            "n_distinct_tribes": len(b["tribes"]),
            "first_year": yrs[0] if yrs else "", "last_year": yrs[-1] if yrs else "",
            "n_years_with_records": len(yrs),
            "publishes_named_participants": int(b["participants"] > 0),
            "publishes_event_location": b["with_location"],
            "publishes_event_dates": b["with_event_date"],
            "records_mentioning_written_comments": b["with_written"],
            "records_mentioning_summary": b["with_summary"],
            "records_mentioning_transcript": b["with_transcript"],
            "consultation_page_url": ";".join(p["url"] for p in pr) or "",
            "consultation_page_status": ";".join(str(p["http_status"]) for p in pr) or "not_probed",
            "policy_frequency_obligation": "", "policy_trigger_obligation": "",
            "policy_source_url": "", "policy_source_quote": "",
            "coverage_basis": "federal_register_full_text",
            "coverage_gap_note": "",
            "fetched_date": TODAY, "built_date": TODAY,
        })

    # policy obligations, from the agency pages we retrieved
    pagedir = RAW / "agency_pages"
    pol = defaultdict(dict)
    for p in probes:
        if str(p.get("http_status")) != "200":
            continue
        host = urllib.parse.urlparse(p["url"]).netloc
        fn = re.sub(r"[^a-z0-9]+", "_",
                    f"{p['agency_key']}_{p['kind']}_{host}".lower())[:120]
        f = pagedir / f"{fn}.txt"
        if not f.exists():
            continue
        t = re.sub(r"\s+", " ", f.read_text(encoding="utf-8", errors="replace"))
        fm = FREQ_RE.search(t)
        tm = TRIGGER_RE.search(t)
        if fm or tm:
            d = pol[p["agency_key"]]
            if fm and not d.get("freq"):
                d["freq"] = fm.group(1).strip()[:400]
            if tm and not d.get("trig"):
                d["trig"] = tm.group(1).strip()[:400]
            d["url"] = p["url"]
            d["quote"] = (fm or tm).group(1).strip()[:600]

    for r in out:
        d = pol.get(r["agency_key"])
        if d:
            r["policy_frequency_obligation"] = d.get("freq", "")
            r["policy_trigger_obligation"] = d.get("trig", "")
            r["policy_source_url"] = d.get("url", "")
            r["policy_source_quote"] = d.get("quote", "")

    # THE AGENCIES THAT PUBLISH NOTHING WE COULD RETRIEVE. Recorded explicitly.
    seen_keys = {r["agency_key"] for r in out if r["agency_key"]}
    for key, label, kind, url in AGENCY_PAGES:
        if key in seen_keys or any(o["agency_key"] == key for o in out):
            continue
        pr = probe_by_key.get(key, [])
        d = pol.get(key, {})
        out.append({
            "agency": label, "parent_department": "", "agency_key": key,
            "n_consultation_events": 0, "n_participant_rows": 0,
            "n_distinct_tribes": 0, "first_year": "", "last_year": "",
            "n_years_with_records": 0, "publishes_named_participants": 0,
            "publishes_event_location": 0, "publishes_event_dates": 0,
            "records_mentioning_written_comments": 0,
            "records_mentioning_summary": 0, "records_mentioning_transcript": 0,
            "consultation_page_url": ";".join(p["url"] for p in pr) or "",
            "consultation_page_status": ";".join(str(p["http_status"]) for p in pr) or "not_probed",
            "policy_frequency_obligation": d.get("freq", ""),
            "policy_trigger_obligation": d.get("trig", ""),
            "policy_source_url": d.get("url", ""),
            "policy_source_quote": d.get("quote", ""),
            "coverage_basis": "agency_page_probe_only",
            "coverage_gap_note": (
                "NO consultation record retrieved for this agency in the "
                "Federal Register consultation corpus. This is a COVERAGE GAP, "
                "not evidence that the agency held no consultations. Agencies "
                "publish consultation unevenly and much of it never reaches the "
                "Federal Register."),
            "fetched_date": TODAY, "built_date": TODAY,
        })
        seen_keys.add(key)

    # ---- what the agency's OWN page did, stated separately from the corpus --
    #
    # Three different things all look like "nothing" and must never be
    # collapsed: an edge WAF refusing an automated client (403), a page that
    # does not exist at any slug we probed (404 - our error until proven
    # otherwise), and a page that returns 200 but renders its content in
    # JavaScript so the bytes carry no text. Only the third is even arguably a
    # statement about the agency, and none of them is a statement about whether
    # the agency consulted.
    for r in out:
        pr = probe_by_key.get(r["agency_key"], [])
        notes = []
        if pr:
            oks = [p for p in pr if str(p["http_status"]) == "200"]
            thin = [p for p in oks if int(p.get("chars") or 0) < 500]
            if not oks and any(str(p["http_status"]) == "403" for p in pr):
                notes.append(
                    "Agency consultation page BLOCKED to automated fetch "
                    "(HTTP 403 from the site's edge). Its published "
                    "consultation material is real and unretrieved; this is an "
                    "access limit, not an absence.")
            elif not oks:
                notes.append(
                    "No agency consultation page returned HTTP 200 at any URL "
                    "probed. Treat as an unlocated page, not a missing one - "
                    "agency slugs move and the obvious URL frequently 404s.")
            elif len(thin) == len(oks):
                notes.append(
                    "Agency consultation page returned HTTP 200 but under 500 "
                    "characters of text: the content is JavaScript-rendered "
                    "and not machine-readable by a plain fetch.")
        else:
            notes.append("Agency consultation page not probed in this build.")

        if r["n_consultation_events"] and not r["publishes_named_participants"]:
            notes.append(
                "Agency appears in the consultation corpus but no record of "
                "its consultations names the participating Tribes. Participant "
                "coverage is a gap for this agency, not an absence of "
                "participants.")
        if notes:
            r["coverage_gap_note"] = (
                (r["coverage_gap_note"] + " ") if r["coverage_gap_note"] else ""
            ) + " ".join(notes)

    out.sort(key=lambda r: (-r["n_consultation_events"], r["agency"]))
    write_csv(CLEAN / "consultation_agency_coverage.csv", out, [
        "agency", "parent_department", "agency_key",
        "n_consultation_events", "n_participant_rows",
        "n_distinct_tribes", "first_year", "last_year", "n_years_with_records",
        "publishes_named_participants", "publishes_event_location",
        "publishes_event_dates", "records_mentioning_written_comments",
        "records_mentioning_summary", "records_mentioning_transcript",
        "consultation_page_url", "consultation_page_status",
        "policy_frequency_obligation", "policy_trigger_obligation",
        "policy_source_url", "policy_source_quote", "coverage_basis",
        "coverage_gap_note", "fetched_date", "built_date"])
    return out


# ---- 3g. report -----------------------------------------------------------

def report(rows, unresolved, stats):
    ev = {r["consultation_event_id"] for r in rows}
    part = [r for r in rows if r["tribe_id"]]
    tribes = {r["tribe_id"] for r in part}

    print("\n--- CONSULTATION EVENTS ---")
    print(f"  consultation events        : {len(ev):,}")
    print(f"  participant rows           : {len(part):,}")
    print(f"  rows with no named participant: {len(rows)-len(part):,}")
    print(f"  distinct Native entities    : {len(tribes):,}")
    print("\n  participant_role")
    for k, v in Counter(r["participant_role"] for r in rows).most_common():
        print(f"    {v:7,d}  {k}")
    print("\n  consultation_type")
    for k, v in Counter(r["consultation_type"] for r in rows).most_common(12):
        print(f"    {v:7,d}  {k}")
    print(f"\n  unresolved participants     : {len(unresolved):,}")
    for k, v in Counter(u["reason"].split(":")[0] for u in unresolved).most_common(10):
        print(f"    {v:7,d}  {k}")

    # ---- who is NEW to the advocacy dataset (never appears in LDA) --------
    lda = set()
    for r in read_csv(CLEAN / "native_entity_lobbying_disclosures.csv"):
        if r.get("entity_id"):
            lda.add(r["entity_id"])
    for r in read_csv(CLEAN / "tribe_year_lobbying_panel.csv"):
        if r.get("entity_id"):
            lda.add(r["entity_id"])
    new = tribes - lda
    print("\n--- ADVOCACY COVERAGE ---")
    print(f"  entities in the LDA lobbying dataset : {len(lda):,}")
    print(f"  entities reached by consultation     : {len(tribes):,}")
    print(f"  NEW to the advocacy dataset (no LDA) : {len(new):,}")
    print("  ^ these entities have a documented government-to-government")
    print("    relationship with a federal agency and NO lobbying filing at all.")
    return len(ev), len(part), len(tribes), len(new)




# =========================================================================
# STAGE 4 - CODEBOOK. VARIABLES ONLY.
# =========================================================================
#
# The codebook is a variable dictionary. Dataset-level prose belongs in
# docs/CONSULTATION_BUILD_LOG.md and would drift if duplicated here.
#
# Scripts 97 and 99 also append to codebook_master.csv, so this re-reads
# the file immediately before writing and only ever ADDS rows whose
# (dataset, variable) pair is absent. A concurrent agent rows are never
# dropped.

CODEBOOK_DATASET = "15_consultation"

CODEBOOK_ENTRIES = [
    ('consultation_events.csv', 'consultation_event_id',
     'Identifier for one consultation. CONS-FR-<Federal Register document number>. Shared by every participant row of the same consultation.'),
    ('consultation_events.csv', 'channel',
     'Advocacy channel, from cedar_domain.AdvocacyChannel. Always CONSULTATION in this file. Consultation is a statutory government-to-government obligation and is NOT lobbying: AdvocacyChannel.CONSULTATION.is_lobbying is False.'),
    ('consultation_events.csv', 'agency',
     'Federal Register parent agency that published the record.'),
    ('consultation_events.csv', 'sub_agency',
     'Federal Register sub-agency. The publishing unit for most records: 1,841 of 2,313 were published by the National Park Service.'),
    ('consultation_events.csv', 'program',
     'The institution or office conducting the consultation where the record names one distinctly from the publishing agency, such as the museum or State Historic Preservation Office in a NAGPRA notice. Blank where the record does not distinguish it.'),
    ('consultation_events.csv', 'consultation_type',
     'What kind of consultation the record is: NAGPRA_consultation_reported, consultation_notice, consultation_session, listening_session, NHPA_section_106, negotiated_rulemaking, dear_tribal_leader_letter, advisory_committee, tribal_summit, NAGPRA.'),
    ('consultation_events.csv', 'topic',
     'Title of the published record.'),
    ('consultation_events.csv', 'notice_date',
     'Federal Register publication date of the record.'),
    ('consultation_events.csv', 'event_start_date',
     'First meeting date, parsed ONLY from a DATES sentence that describes a meeting and is not the comment deadline. Blank where the record states no meeting date; blank is silence, never zero.'),
    ('consultation_events.csv', 'event_end_date',
     'Last meeting date, on the same basis as event_start_date.'),
    ('consultation_events.csv', 'location',
     "City, State strings parsed from the record's ADDRESSES section, semicolon-separated. Blank where none is published."),
    ('consultation_events.csv', 'format',
     "Semicolon-separated observed formats: in_person, virtual, teleconference, written_comment. Derived from the record's own wording."),
    ('consultation_events.csv', 'tribe_id',
     'Cedar entity spine ID of the participating Native government. Blank where the record names no participants.'),
    ('consultation_events.csv', 'tribe_name',
     'Canonical spine name of the participating entity.'),
    ('consultation_events.csv', 'participant_name_as_published',
     "The participant's name VERBATIM as printed in the record, kept beside our resolution of it so any attribution can be audited against the source."),
    ('consultation_events.csv', 'participant_role',
     'What the record says this entity DID. consulted = the record states consultation was held with it; invited_did_not_participate = the record states it was contacted or invited and did not attend; invited = invited, outcome unstated; not_enumerated = the consultation is real but the record names no participants. A role is NEVER upgraded: an invited Tribe is not a present Tribe.'),
    ('consultation_events.csv', 'comment_deadline',
     'Comment close date, from the Federal Register structured comments_close_on field where present, otherwise from a DATES sentence explicitly about comments.'),
    ('consultation_events.csv', 'has_written_comments',
     '1 where the record mentions written comments. An indicator that the record REFERS to them, not that Cedar holds them.'),
    ('consultation_events.csv', 'has_summary',
     '1 where the record mentions a consultation summary or report.'),
    ('consultation_events.csv', 'has_transcript',
     '1 where the record mentions a transcript.'),
    ('consultation_events.csv', 'federal_register_citation',
     'Volume and page citation, such as 76 FR 7232.'),
    ('consultation_events.csv', 'source_url',
     'Federal Register URL for the record.'),
    ('consultation_events.csv', 'source_quote',
     'The verbatim sentence that assigns this participant its role. Every participant row carries the sentence it came from.'),
    ('consultation_events.csv', 'fetched_date',
     'Date the source text was retrieved.'),
    ('consultation_events.csv', 'tier',
     'A/B/C/X per cedar_domain.Tier. Every row is B: one parsed federal record is a single leg of evidence, and tier A requires a human ruling or two independent legs.'),
    ('consultation_events.csv', 'confidence',
     'high where the participant matched an official Federal Register name, a name head, or an enumerated constituent band; medium for weaker resolutions.'),
    ('consultation_events.csv', 'built_date',
     'Date this file was built.'),
    ('consultation_events.csv', 'match_method',
     'How the published name was resolved to the spine: fr_official_name, fr_official_prefix, name_head, government_class_core, constituent_band_in_parenthetical, exact_canonical, resolve_entity_alias, or the same with _via_former_name.'),
    ('consultation_agency_coverage.csv', 'agency',
     'The publishing agency, taken as the sub-agency where the record has one. Keying on the parent department alone would report the National Park Service as publishing nothing while it published 1,841 of the 2,313 records.'),
    ('consultation_agency_coverage.csv', 'parent_department',
     'Cabinet department above the publishing agency, where the record names one.'),
    ('consultation_agency_coverage.csv', 'agency_key',
     'Short key for the agencies whose own consultation pages were probed.'),
    ('consultation_agency_coverage.csv', 'n_consultation_events',
     'Distinct consultations attributed to this agency in the corpus.'),
    ('consultation_agency_coverage.csv', 'n_participant_rows',
     'Participant rows: consultation-by-named-entity pairs.'),
    ('consultation_agency_coverage.csv', 'n_distinct_tribes',
     "Distinct Native entities this agency's records name."),
    ('consultation_agency_coverage.csv', 'first_year',
     'Earliest publication year observed for this agency.'),
    ('consultation_agency_coverage.csv', 'last_year',
     'Latest publication year observed for this agency.'),
    ('consultation_agency_coverage.csv', 'n_years_with_records',
     'Number of distinct years in which this agency published a consultation record. Gaps between first_year and last_year are coverage gaps, not quiet years.'),
    ('consultation_agency_coverage.csv', 'publishes_named_participants',
     '1 where any record from this agency names the participating Tribes. 0 for 12 of the 13 agencies worked.'),
    ('consultation_agency_coverage.csv', 'publishes_event_location',
     "Count of this agency's rows carrying a parsed location."),
    ('consultation_agency_coverage.csv', 'publishes_event_dates',
     "Count of this agency's rows carrying a parsed meeting date."),
    ('consultation_agency_coverage.csv', 'records_mentioning_written_comments',
     'Count of rows whose record mentions written comments.'),
    ('consultation_agency_coverage.csv', 'records_mentioning_summary',
     'Count of rows whose record mentions a consultation summary or report.'),
    ('consultation_agency_coverage.csv', 'records_mentioning_transcript',
     'Count of rows whose record mentions a transcript.'),
    ('consultation_agency_coverage.csv', 'consultation_page_url',
     "The agency's own consultation or policy pages probed, semicolon-separated."),
    ('consultation_agency_coverage.csv', 'consultation_page_status',
     'HTTP status per probed URL. 403 means an edge WAF refused an automated client; 404 means no page was found at the slug probed and should be read as our error until proven otherwise; not_probed means the agency was outside the 13 worked.'),
    ('consultation_agency_coverage.csv', 'policy_frequency_obligation',
     'Verbatim published text stating a required consultation frequency, where the agency publishes one.'),
    ('consultation_agency_coverage.csv', 'policy_trigger_obligation',
     'Verbatim published text stating when consultation is required, where the agency publishes one. A published obligation is a map to records nobody has pulled.'),
    ('consultation_agency_coverage.csv', 'policy_source_url',
     'URL the policy obligation text was read from.'),
    ('consultation_agency_coverage.csv', 'policy_source_quote',
     'Verbatim quote supporting the policy obligation fields.'),
    ('consultation_agency_coverage.csv', 'coverage_basis',
     'federal_register_full_text where the agency appears in the corpus; agency_page_probe_only where it does not.'),
    ('consultation_agency_coverage.csv', 'coverage_gap_note',
     'What is missing and WHY. Distinguishes an edge block, an unlocated page, a JavaScript-rendered page, and an agency whose records name no participants. None of these is evidence that consultations did not happen.'),
    ('consultation_agency_coverage.csv', 'fetched_date',
     'Date the agency page was probed.'),
    ('consultation_agency_coverage.csv', 'built_date',
     'Date this file was built.'),
]


def _type_units(var):
    v = var.lower()
    if (v.startswith("n_") or v.startswith("records_mentioning")
            or v.startswith("publishes_")):
        return "integer", "count"
    if v.startswith("has_"):
        return "integer", "0/1"
    if v.endswith("_date") or v.endswith("_deadline"):
        return "text", "YYYY-MM-DD"
    if v.endswith("_year"):
        return "integer", "year"
    if v.endswith("_url"):
        return "text", "URL"
    if v.endswith("_id"):
        return "text", "code"
    return "text", "text"


def stage_codebook():
    print("=== 96 stage CODEBOOK (variables only) ===")
    p = CLEAN / "codebook_master.csv"
    rows = read_csv(p)
    if not rows:
        print("  codebook_master.csv missing; skipping")
        return
    fields = list(rows[0].keys())
    srcs = {
        "consultation_events.csv":
            read_csv(CLEAN / "consultation_events.csv"),
        "consultation_agency_coverage.csv":
            read_csv(CLEAN / "consultation_agency_coverage.csv"),
    }
    have = {((r.get("dataset") or "").strip().lower(),
             (r.get("variable") or "").strip().lower()) for r in rows}
    added = 0
    for fname, var, desc in CODEBOOK_ENTRIES:
        if (CODEBOOK_DATASET, var.lower()) in have:
            continue
        src = srcs.get(fname) or []
        n = len(src)
        # Fill rates are MEASURED from the data, never asserted.
        filled = (sum(1 for r in src if (r.get(var) or "").strip())
                  if n else 0)
        t, u = _type_units(var)
        new = {c: "" for c in fields}
        new.update({
            "dataset": CODEBOOK_DATASET, "variable": var, "type": t,
            "units": u,
            "pct_filled": ("%.1f" % (100.0 * filled / n)) if n else "0.0",
            "n_rows": str(n), "published": "1",
            "access_tier": "public", "description": desc,
            "generated": TODAY,
        })
        rows.append(new)
        have.add((CODEBOOK_DATASET, var.lower()))
        added += 1
    if added:
        bak = p.with_suffix(".csv.bak_%s_pre96" % TODAY)
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
        write_csv(p, rows, fields)
    print("  added %d variable entries (%s total)"
          % (added, format(len(rows), ",")))

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "fetch":
        stage_fetch()
    elif cmd == "agencies":
        stage_agencies()
    elif cmd == "build":
        stage_build()
        stage_codebook()
    elif cmd == "codebook":
        stage_codebook()
    elif cmd == "all":
        stage_fetch()
        stage_agencies()
        stage_build()
        stage_codebook()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
