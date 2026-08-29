#!/usr/bin/env python3
"""
Cedar Press - 104: Washington machine allocation + inter-tribal transfer ledger.

WHY THIS EXISTS
---------------
Elijah, 2026-08-07:

    "washington has a slot allowance per tribe and tribes can give them to other
     tribes, so not every tribe in WA has a casino but they can give their slot
     to another more successful tribe."

Washington does not cap machines per casino and stop there. It gives EVERY
federally recognised tribe in the state a per-tribe entitlement of Tribal
Lottery System Player Terminals - an "Allocation" - whether or not that tribe
operates a casino, and it lets a tribe operate or TRANSFER the ability to
operate those terminals to another Washington tribe. The consequence is a
market in machine rights between Native governments, which is the same shape as
ANCSA 7(i) sharing or California's RSTF: money moving BETWEEN Native entities,
invisible to every federal dataset.

WHAT THIS BUILDS
----------------
1. data/clean/wa_machine_allocations.csv
   Per tribe, per effective period: the entitlement stated in the instrument.
   `measurement_type` is AUTHORIZED_MAXIMUM on EVERY row, always. A tribe may
   hold an Allocation it does not operate - that is the entire point of the
   transfer market - so this can never become an operating count. The build
   asserts `may_promote(AUTHORIZED_MAXIMUM, ACTIVE_FLOOR_COUNT) is False`.

2. data/clean/wa_machine_transfers.csv
   The ledger, modelled the way `native_passthrough.csv` models subaward
   pass-through: an EVENT with a FROM party and a TO party, both resolved
   through the spine, never collapsed into the receiving tribe's count.

WHAT WASHINGTON DOES NOT PUBLISH  (measured, not assumed - see the build log)
----------------------------------------------------------------------------
The Appendix D "Class III Gaming Station Transfer Agreement" appended to every
Washington compact is a BLANK FORM. The executed agreements are not published.
Appendix X2 s12.2.2 puts the terminal-transfer plan in the hands of the tribes
and says of the State: "The State shall have no responsibility whatsoever with
respect to the plan". And Appendix D s4 places the price in a document that is
never filed:

    "Transferor and Transferee may enter into separate agreements related to
     the utilization of Class III Gaming Stations transferred hereby"

So the transfer ledger ships with the schema and zero rows unless an executed
agreement is in evidence. A documented empty ledger with the clause that makes
it empty is a finding; an invented one is fabrication.

READS
  data/clean/compact_versions.csv           181 Washington version records
  data/raw/external/compacts/text/*.txt     the instrument text under each
  data/raw/external/wa_gaming/*.html        WSGC pages (fetched by this script)
  data/spine/cedar_entity_spine.csv

WRITES
  data/clean/wa_machine_allocations.csv
  data/clean/wa_machine_transfers.csv
  data/raw/external/wa_gaming/_SOURCE_MANIFEST.csv
  review/wa_allocation_unresolved_<date>.csv
  docs/WA_ALLOCATION_BUILD_LOG.md           (facts only; prose is hand-written)
  data/clean/codebook_master.csv            (appended: variables only)
"""

import csv
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
LOGS = CEDAR / "logs"
RAW = CEDAR / "data" / "raw" / "external" / "wa_gaming"
CTEXT = CEDAR / "data" / "raw" / "external" / "compacts" / "text"
TODAY = date.today().isoformat()

HOST = "www.wsgc.wa.gov"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# ---------------------------------------------------------------------------
# SHARED VOCABULARY - imported, never re-declared (spec 13.1).
# ---------------------------------------------------------------------------
sys.path.insert(0, str(CEDAR / "code"))
from cedar_domain import MeasurementType, may_promote, NAME_TRAPS, Tier  # noqa: E402
from cedar_keys import surrogate_id                            # noqa: E402

# --------------------------------------------------------------------------
# THE PRIMARY KEY OF wa_machine_allocations.csv, AND WHAT IT IS MADE OF
#
# `allocation_id` used to be `f"WAALLOC-{n:04d}"` where `n` was a counter
# running across every tribe in the build - a POSITION. Re-running against a
# source that gained one tribe renumbered every allocation after it, so a
# merge on the id would have appended duplicates rather than matched.
#
# It is now a deterministic blake2b digest of the three things the compact or
# appendix itself states: WHICH TRIBE, the date the instrument took EFFECT,
# and WHAT was measured. Measured 2026-08-26: unique over all 75 rows,
# 0 blank.
#
# Migrated in the live file by `327_migrate_class7_keys_to_digests.py`.
# --------------------------------------------------------------------------
WA_ALLOCATION_KEY_COLUMNS = ["tribe_name", "effective_start",
                             "measurement_type"]

_spec = importlib.util.spec_from_file_location(
    "m33", str(CEDAR / "code" / "33_apply_party_rulings.py"))
m33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m33)
resolve_entity, norm, core = m33.resolve_entity, m33.norm, m33.core

# The whole dataset stands on this one rule. Assert it before writing a row.
assert may_promote(MeasurementType.AUTHORIZED_MAXIMUM,
                   MeasurementType.ACTIVE_FLOOR_COUNT) is False, \
    "AUTHORIZED_MAXIMUM must never promote to ACTIVE_FLOOR_COUNT"
assert may_promote(MeasurementType.AUTHORIZED_MAXIMUM,
                   MeasurementType.COMPACT_REPORTED_COUNT) is True

AUTH = MeasurementType.AUTHORIZED_MAXIMUM.value


# ---------------------------------------------------------------------------
# io helpers
# ---------------------------------------------------------------------------
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


def squash(s):
    """Collapse whitespace. PDF text carries hard line breaks mid-sentence."""
    return re.sub(r"\s+", " ", s or "").strip()


def clean_quote(s, limit=600):
    """Verbatim, whitespace-normalised, control chars stripped. Never edited."""
    s = squash(s)
    s = "".join(c for c in s if c == " " or c.isprintable())
    return s[:limit]


# ---------------------------------------------------------------------------
# STAGE 1 - fetch. One host, one stream, lock claimed. Idempotent: a file
# already on disk is not re-fetched, so a re-run costs the host nothing.
# ---------------------------------------------------------------------------
FETCH_LOG = []


def hostlock(active=True, note=""):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    if p.exists():
        d = json.loads(p.read_text())
    else:
        d = {"host": HOST, "queue": []}
    d.update({"pid": os.getpid(), "script": "code/104_build_wa_allocations.py",
              "active": active, "note": note or d.get("note", ""),
              "policy": "single stream, >=2.5s gap, idempotent skip-if-present"})
    d["started" if active else "released"] = datetime.now().isoformat()
    p.write_text(json.dumps(d, indent=1))


def get(url, fname, force=False):
    dest = RAW / fname
    if dest.exists() and not force:
        FETCH_LOG.append(dict(file=fname, url=url, http_status="cached",
                              bytes=dest.stat().st_size, fetched_date=TODAY))
        return 200, dest.read_bytes()
    cmd = ["curl", "-s", "-L", "-A", UA, "--max-time", "60",
           "-w", "\n__S__%{http_code}", url]
    out = subprocess.run(cmd, capture_output=True).stdout
    m = re.search(rb"\n__S__(\d+)$", out)
    status = int(m.group(1)) if m else 0
    body = out[:m.start()] if m else out
    # Archive whatever came back, but record the status alongside it. CHECK THE
    # HTTP STATUS, NOT THE FILE: a Drupal 404 body still contains <main>, so
    # every parser below reads only files the manifest records as 200.
    dest.write_bytes(body)
    FETCH_LOG.append(dict(file=fname, url=url, http_status=status,
                          bytes=len(body), fetched_date=TODAY))
    print(f"    {status}  {len(body):>7,}  {url}")
    time.sleep(2.5)
    return status, body


def stage_fetch():
    print("\n[1] WSGC fetch (idempotent)")
    RAW.mkdir(parents=True, exist_ok=True)
    hostlock(True, "WA machine allocation + inter-tribal transfer ledger")
    pages = [
        ("https://www.wsgc.wa.gov/tribal-partnerships/tribal-lottery-system",
         "wsgc_tls_2026-08-07.html"),
        ("https://www.wsgc.wa.gov/tribal-partnerships/tribal-casino-locations",
         "wsgc_casino_locations_2026-08-07.html"),
        ("https://www.wsgc.wa.gov/tribal-partnerships/"
         "tribal-gaming-compacts-and-amendments",
         "wsgc_compacts_index_2026-08-07.html"),
        ("https://www.wsgc.wa.gov/tribal-partnerships",
         "wsgc_tribal_partnerships_2026-08-07.html"),
    ]
    for u, f in pages:
        get(u, f)

    # NEGATIVE PROBES. The claim "WSGC publishes no allocation or transfer
    # table" is only worth anything if the absence is measured, so the URLs a
    # reasonable person would try are fetched every run and their status codes
    # recorded. CHECK THE HTTP STATUS, NOT THE FILE: a Drupal 404 body is 44 KB
    # and contains <main>, so a parser that trusts "the file has content" would
    # ship these as pages.
    print("    negative probes (absence must be measured, not assumed)")
    for u, f in [
        ("https://www.wsgc.wa.gov/robots.txt", "wsgc_robots.txt"),
        ("https://www.wsgc.wa.gov/about-us", "wsgc_about.html"),
        ("https://www.wsgc.wa.gov/about-us/about-washington-state-gambling-"
         "commission", "wsgc_about_agency.html"),
        ("https://www.wsgc.wa.gov/news/rss.xml", "wsgc_news_rss.xml"),
        ("https://www.wsgc.wa.gov/sitemap.xml", "wsgc_sitemap.xml"),
        ("https://www.wsgc.wa.gov/sitemap.xml?page=1", "wsgc_sitemap_p1.xml"),
        ("https://www.wsgc.wa.gov/about-us/reports", "wsgc_reports.html"),
        ("https://www.wsgc.wa.gov/about-us/reports-and-data",
         "wsgc_reports_data.html"),
        ("https://www.wsgc.wa.gov/about-us/publications",
         "wsgc_publications.html"),
        ("https://www.wsgc.wa.gov/search?keys=allocation",
         "wsgc_search_allocation.html"),
        ("https://www.wsgc.wa.gov/search?keys=transfer%20agreement",
         "wsgc_search_transfer.html"),
        ("https://www.wsgc.wa.gov/search?keys=annual%20report",
         "wsgc_search_annualreport.html"),
    ]:
        get(u, f, force=True)

    idx = (RAW / "wsgc_compacts_index_2026-08-07.html").read_text(
        encoding="utf-8", errors="replace")
    links = sorted(set(re.findall(
        r'href="(/tribal-partnerships/tribal-gaming-compacts-and-amendments/'
        r'[^"]+)"', idx)))
    assert len(links) >= 29, (
        f"WSGC compacts index yielded {len(links)} tribe links; Washington has "
        "29 compacted tribes. Refusing to build a short universe.")
    print(f"    {len(links)} per-tribe compact pages")
    for l in links:
        get("https://www.wsgc.wa.gov" + l,
            f"wsgc_compact_page_{l.rsplit('/', 1)[-1]}.html")
    hostlock(False)
    return links


def stage_manifest():
    """md5 every raw artefact. Provenance is a column, not a memory."""
    rows = []
    by_file = {r["file"]: r for r in FETCH_LOG}
    for p in sorted(RAW.glob("*")):
        if p.is_dir() or p.name.startswith("_"):
            continue
        h = hashlib.md5(p.read_bytes()).hexdigest()
        f = by_file.get(p.name, {})
        rows.append(dict(file=p.name, url=f.get("url", ""),
                         http_status=f.get("http_status", ""),
                         bytes=p.stat().st_size, md5=h,
                         fetched_date=f.get("fetched_date", TODAY),
                         source_authority="Washington State Gambling Commission"))
    write_csv(RAW / "_SOURCE_MANIFEST.csv", rows,
              ["file", "url", "http_status", "bytes", "md5", "fetched_date",
               "source_authority"])
    return rows


# ---------------------------------------------------------------------------
# STAGE 2 - WSGC per-tribe amendment index. Gives the STATE signature date,
# which is a different fact from the Secretarial approval date and must not be
# silently substituted for it.
# ---------------------------------------------------------------------------
def html_text(p):
    t = Path(p).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"(?s)<main.*?</main>", t)
    b = m.group(0) if m else t
    b = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", "", b)
    b = re.sub(r"<[^>]+>", " ", b)
    import html as _h
    return squash(_h.unescape(b))


def stage_wsgc_amendments():
    print("\n[2] WSGC per-tribe amendment index")
    out = []
    for p in sorted(RAW.glob("wsgc_compact_page_*.html")):
        t = html_text(p)
        m = re.search(r"compact amendments WSGC has negotiated with the (.+?)\.",
                      t)
        tribe = m.group(1).strip() if m else ""
        body = t[t.find("Original Compact"):] if "Original Compact" in t else t
        for mm in re.finditer(
                r"([A-Za-z0-9 ]{0,40}?[Aa]mendment[^.]{0,120}?|Memorandum of "
                r"Incorporation)[^.]{0,120}?[Ss]igned (\d{2}/\d{2}/\d{4})"
                r"(,? this amendment[^.]{0,400}\.)?", body):
            out.append(dict(
                wsgc_tribe_name=tribe,
                amendment_label=squash(mm.group(1))[:90],
                state_signed_date=datetime.strptime(
                    mm.group(2), "%m/%d/%Y").date().isoformat(),
                subject=clean_quote(mm.group(3) or "", 300),
                source_file=p.name))
        for mm in re.finditer(r"signed the original[^.]{0,120}?on (\d{2}/\d{2}/\d{4})",
                              body):
            out.append(dict(
                wsgc_tribe_name=tribe, amendment_label="original compact",
                state_signed_date=datetime.strptime(
                    mm.group(1), "%m/%d/%Y").date().isoformat(),
                subject="", source_file=p.name))
    print(f"    {len(out)} dated instruments across "
          f"{len({r['wsgc_tribe_name'] for r in out})} tribes")
    return out


def stage_casino_operators():
    """WSGC's own list of tribes that OPERATE a compacted Class III casino.

    Absence from this list is not absence of a casino in general - WSGC lists
    Class III compacted casinos only, so a Class II bingo hall is invisible
    here. Absence under a filter is a property of the filter.
    """
    p = RAW / "wsgc_casino_locations_2026-08-07.html"
    t = p.read_text(encoding="utf-8", errors="replace")
    import html as _h
    ops = []
    for s in re.finditer(r'(?s)<select[^>]*name="(tid_entityreference_filter)"'
                         r'[^>]*>(.*?)</select>', t):
        for o in re.findall(r"<option[^>]*>(.*?)</option>", s.group(2)):
            v = squash(_h.unescape(o))
            if v and not v.startswith("-"):
                ops.append(v)
    txt = html_text(p)
    claim = re.search(r"There are (\d+) federally recognized tribes[^.]*\. "
                      r"(\d+) tribes operate (\d+) casinos under compact", txt)
    shown = re.search(r"Showing 1 - (\d+) of (\d+) results", txt)
    return ops, (claim.groups() if claim else None), \
        (shown.groups() if shown else None), txt


# ---------------------------------------------------------------------------
# STAGE 3 - the instruments. Every number here is lifted verbatim from the
# compact text with the sentence that states it.
# ---------------------------------------------------------------------------

# Appendix X2 s12.1 and the 2015+ Addendum amendment of it. One clause, one
# number, one regime. The OCR of these PDFs turns "1075" into "I 075" and
# curly quotes into replacement chars, so the number group tolerates that and
# nothing else.
RE_X2 = re.compile(
    r"entitled to an [Aa]llocation of,? ?and ?may operate or ?transfer ?the "
    r"ability to operate,? ?up to ([\dIl]{3,5}) Player ?Terminals", re.I)

# Appendix X (1998) s12.1: an initial allocation that STEPS UP on a compliance
# review. Two numbers, one regime - base 425, +250 conditional, total 675.
RE_X_INIT = re.compile(
    r"Initial Allocation\.? +During the first year of operations under this "
    r"Appendix\.?,? +the Tribe shall be entitled to an allocation and "
    r"operation of (\d{3}) Player Terminals", re.I)
# The character class is [rnm], not [rn]: these PDFs OCR "Terminals" as
# "Tenninals" and "Te1minals", and a class that could not also match a plain
# "rm" silently dropped the step-up from 20 of 21 Appendix X documents.
RE_X_STEP = re.compile(
    r"the Tribe.{0,3}s Allocation shall be increased to (\d{3}) Player "
    r"Te[rnm1]{2}inals", re.I)

# Appendix Spokane (2007) - a tribe-specific allocation, not the statewide one.
RE_SPOKANE = re.compile(
    r"entitled to an allocation of nine hundred \((\d{3})\) player terminals",
    re.I)

# Appendix Colville - the same transferable structure denominated in Electronic
# Gaming Devices rather than Player Terminals. The two units interoperate in
# the market by the clause's own terms, so both belong in this ledger.
RE_COLVILLE = re.compile(
    r"the Tribes shall be entitled to an allocation and shall be permitted to "
    r"operate up to and including ([\d,]{3,6}) EGDs", re.I)

# Transfer rules. Recorded for the build log; they are the reason the ledger
# is shaped the way it is.
RULE_PATTERNS = {
    "transfer_authority_x2": re.compile(
        r"The Tribe may acquire the ability to operate additional Player "
        r"Terminals[^.]{0,400}\.", re.I),
    "tribal_plan_state_disclaims": re.compile(
        r"The State shall have no responsibility whatsoever with respect to "
        r"the plan[^.]{0,400}\.", re.I),
    "state_receives_count_only": re.compile(
        r"until it completes delivery to the State of documentation "
        r"conf[oi]rming the number of transfers[^.]{0,200}\.", re.I),
    "state_receives_full_documents": re.compile(
        r"until 30 days has elapsed following delivery to the State of a "
        r"complete set of the documents which govern the transfer", re.I),
    "consideration_in_separate_agreement": re.compile(
        r"Transferor and Transferee may enter into separate agreements "
        r"related to the utilization of Class III Gaming Stations[^.]{0,300}\.",
        re.I),
    "appendix_d_form": re.compile(
        r"shall be effectuated through the use of a .{0,4}Class III Gaming "
        r"Station Transfer Agreement.{0,4} substantially in the form appended "
        r"hereto as Appendix D", re.I),
    "escalator_50": re.compile(
        r"The Tribe.{0,3}s Allocation of Player Terminals as set forth in "
        r"Appendix X2 may increase by 50 Player Terminals[^.]{0,200}\.", re.I),
    "escalator_extends_to_all": re.compile(
        r"the Tribe shall be automatically entitled to the same Allocation "
        r"increase authorized to that other Wash[^.]{0,200}\.", re.I),
    "facility_and_total_ceiling": re.compile(
        r"the Tribe may operate no more than\s+([\d,]+)\s+Player Terminals per "
        r"facility[^.]{0,600}\.", re.I),
    "facility_ceiling_1500": re.compile(
        r"up to a maximum of 1500 Player Terminals per facility, by acquiring "
        r"allocation rights from any tribe[^.]{0,300}\.", re.I),
    "colville_egd_ceiling": re.compile(
        r"the Tribes shall be permitted to operate up to a total of ([\d,]+) "
        r"EGDs by acquiring allocation rights[^.]{0,300}\.", re.I),
}

# An EXECUTED transfer would name two tribes and a number in one instrument.
# Nothing in the corpus matches; the pattern is kept so a future document that
# does match is picked up instead of being missed.
RE_EXECUTED = re.compile(
    r"(?:Transferor|Transferee)[^.]{0,40}?(?:is|means|:)\s*"
    r"(?:the\s+)?([A-Z][A-Za-z'\- ]{3,45}?(?:Tribe|Nation|Community|Tribes))",
    re.S)


def num(s):
    """OCR-tolerant integer. 'I 075' and '1,075' are both 1075."""
    s = s.replace("I", "1").replace("l", "1").replace(",", "").replace(" ", "")
    return int(s)


def context(text, m, before=260, after=340):
    return clean_quote(text[max(0, m.start() - before): m.end() + after])


def stage_instruments():
    print("\n[3] instrument extraction")
    versions = [r for r in read_csv(CLEAN / "compact_versions.csv")
                if (r.get("compact_id") or "").startswith("CMP-WA-")]
    compacts = {r["compact_id"]: r for r in read_csv(CLEAN / "compacts.csv")}
    print(f"    {len(versions)} Washington compact versions")

    found, rules = [], []
    missing_text = 0
    for v in versions:
        tp = CTEXT / (v.get("text_path") or "")
        if not tp.exists():
            missing_text += 1
            continue
        raw = tp.read_text(encoding="utf-8", errors="replace")
        t = squash(raw)
        c = compacts.get(v["compact_id"], {})
        common = dict(
            compact_id=v["compact_id"], version_id=v["version_id"],
            amendment_number=v.get("amendment_number", ""),
            approval_date=v.get("approval_date", ""),
            tribe_name_as_published=c.get("tribe") or v.get("bia_tribes_column", ""),
            source_url=v.get("source_url", ""),
            source_pdf=v.get("source_pdf", ""),
            bia_title=v.get("bia_title", ""))

        for name, pat in RULE_PATTERNS.items():
            for m in pat.finditer(t):
                rules.append(dict(common, rule=name, quote=context(t, m, 60, 60)))

        # PRECEDENCE WITHIN ONE DOCUMENT.
        # A restated Washington compact reprints its whole appendix history, so
        # the 2022 Chehalis instrument contains Appendix X's 425-terminal
        # Initial Allocation AND Appendix X2's 1,075 side by side. Reading both
        # as facts about 2022 put six tribes back on a 1998 number. Appendix X2
        # s12.1 states the Allocation; Appendix X survives in the document only
        # as the regime under which pre-X2 terminals may keep operating
        # (Appendix X2 s1). So for player terminals, the highest-precedence
        # clause present in a document is the one that governs it.
        pt = []
        m = RE_X2.search(t)
        if m:
            n = num(m.group(1))
            pt.append((3, dict(common, base=n, additional=0, total=n,
                               instrument=("Appendix X2 Addendum s2 (amending "
                                           "Appendix X2 s12.1)" if n > 975
                                           else "Appendix X2 s12.1"),
                               unit="player_terminals",
                               conditional=0, quote=context(t, m))))
        msp = RE_SPOKANE.search(t)
        if msp:
            n = num(msp.group(1))
            pt.append((2, dict(common, base=n, additional=0, total=n,
                               instrument="Appendix Spokane s5",
                               unit="player_terminals",
                               conditional=0, quote=context(t, msp))))
        mi = RE_X_INIT.search(t)
        if mi:
            base = num(mi.group(1))
            ms = RE_X_STEP.search(t)
            step = num(ms.group(1)) if ms else base
            pt.append((1, dict(
                common, base=base, additional=step - base, total=step,
                instrument="Appendix X s12.1 (initial) and s12.2 (compliance step-up)",
                unit="player_terminals", conditional=1 if ms else 0,
                quote=context(t, mi)
                + (" || " + context(t, ms, 60, 200) if ms else ""))))
        if pt:
            rank, best = max(pt, key=lambda x: x[0])
            if len(pt) > 1:
                superseded = "; ".join(sorted(
                    p["instrument"] for r_, p in pt if r_ != rank))
                best = dict(best, instrument=(
                    best["instrument"]
                    + f" [document also reprints {superseded}, superseded]"))
            found.append(best)

        # A separate device class with its own entitlement, not a competing
        # statement of the same one, so it is NOT ranked against the above.
        mc = RE_COLVILLE.search(t)
        if mc:
            n = num(mc.group(1))
            found.append(dict(common, base=n, additional=0, total=n,
                              instrument="Appendix Colville s2",
                              unit="electronic_gaming_devices",
                              conditional=0, quote=context(t, mc)))

    print(f"    {len(found)} allocation clauses, {len(rules)} rule clauses"
          f"{f', {missing_text} versions without text' if missing_text else ''}")
    return found, rules, versions


# ---------------------------------------------------------------------------
# STAGE 4 - resolve to the spine.
#
# Washington is full of near-identical names and the spine stores SHORT
# canonical names. Three guards, all measured against the 15 Washington rows in
# review/spine_short_name_collisions_2026-08-07.csv:
#
#   1. GOVERNMENT CLASS ONLY. A compact party is a federally recognised tribe
#      by definition. This alone kills the five HIGH-risk Washington
#      collisions - Chehalis Tribal Loan Fund, Jamestown S'Klallam Tribal
#      Capital, Lummi Nation School, Muckleshoot Tribal School, Quileute
#      Tribal School - none of which can be a compact signatory.
#   2. RECORD AT LEAST AS SPECIFIC AS THE ENTITY. Accept containment only when
#      the entity's core tokens are a SUBSET of the record's. "Lower Elwha
#      Klallam Tribe" -> "Lower Elwha" passes; the reverse direction, which is
#      what booked $2.8B onto a school on 2026-08-06, cannot.
#   3. NAME_TRAPS. A match whose entire overlap is trap tokens never links.
# ---------------------------------------------------------------------------
GOV_CLASSES = {"Federally recognized tribe",
               "Federally recognized Alaska Native Village",
               "State-recognized tribe"}


def resolve_tribe(name, spine):
    tid, canon, how = resolve_entity(name, spine)
    if not tid:
        return None, None, how
    row = next((r for r in spine if r["tribe_id"] == tid), None)
    if not row or row.get("entity_class") not in GOV_CLASSES:
        return None, None, (f"not_a_government_class:"
                            f"{row.get('entity_class') if row else '?'}")
    ec, rc = core(row["canonical_name"]), core(name)
    if how == "containment" and not ec <= rc:
        return None, None, "entity_more_specific_than_record"
    overlap = ec & rc
    if overlap and all(t in NAME_TRAPS for t in overlap):
        return None, None, f"name_trap_only_overlap:{sorted(overlap)}"
    return tid, row["canonical_name"], how


# ---------------------------------------------------------------------------
# STAGE 5 - periods. An allocation runs until the next instrument replaces it.
# ---------------------------------------------------------------------------
def stage_periods(found, spine):
    print("\n[4] resolve + build periods")
    resolved, unresolved = [], []
    for f in found:
        nm = f["tribe_name_as_published"]
        tid, canon, how = resolve_tribe(nm, spine)
        if tid:
            resolved.append(dict(f, tribe_id=tid, tribe_name=canon,
                                 match_method=how))
        else:
            unresolved.append(dict(f, reason=how))
    print(f"    resolved {len(resolved)}  unresolved {len(unresolved)}")

    # A series runs per (tribe, DEVICE UNIT). Colville's Appendix Colville
    # entitlement is denominated in Electronic Gaming Devices and its Appendix
    # X2 entitlement in Player Terminals; chaining them together would have
    # one silently end the other, which no instrument says.
    by_tribe = defaultdict(list)
    for r in resolved:
        by_tribe[(r["tribe_id"], r["unit"])].append(r)

    rows, n = [], 0
    for tid, unit in sorted(by_tribe):
        # Sort by effective date, then collapse consecutive duplicates of the
        # same entitlement: a later amendment that does not change s12.1
        # restates it, and restatement is not a new regime.
        seq = sorted(by_tribe[(tid, unit)],
                     key=lambda r: (r["approval_date"] or "9999",
                                    r["version_id"]))
        kept = []
        for r in seq:
            if kept and kept[-1]["total"] == r["total"]:
                kept[-1]["restated_by"].append(r["version_id"])
                continue
            kept.append(dict(r, restated_by=[]))
        for i, r in enumerate(kept):
            start = r["approval_date"] or ""
            end = ""
            if i + 1 < len(kept) and kept[i + 1]["approval_date"]:
                nxt = datetime.strptime(kept[i + 1]["approval_date"],
                                        "%Y-%m-%d").date()
                end = (nxt - timedelta(days=1)).isoformat()
            n += 1
            cite = (f"{r['instrument']}; unit={r['unit']}; "
                    f"{r['version_id']}; Secretarial approval / Federal "
                    f"Register publication {start or 'undated'}")
            if r["restated_by"]:
                cite += (f"; restated without change by "
                         f"{', '.join(r['restated_by'][:4])}")
            row = dict(
                allocation_id="",          # set below, from THIS row's facts
                tribe_id=tid, tribe_name=r["tribe_name"],
                base_allocation=r["base"],
                additional_allocated=r["additional"],
                total_authorized=r["total"],
                effective_start=start, effective_end=end,
                measurement_type=AUTH,
                compact_or_appendix_cite=cite,
                source_url=r["source_url"],
                source_quote=r["quote"],
                fetched_date=TODAY, tier=Tier.A.value,
                confidence=("instrument_stated_conditional"
                            if r["conditional"] else "instrument_stated"),
                built_date=TODAY,
                # internal only - write_csv uses extrasaction="ignore"
                _unit=unit)
            row["allocation_id"] = surrogate_id(
                "WAALLOC", row, WA_ALLOCATION_KEY_COLUMNS)
            rows.append(row)
    return rows, unresolved


# ---------------------------------------------------------------------------
# STAGE 6 - the transfer ledger.
# ---------------------------------------------------------------------------
def stage_transfers(spine):
    """Search every Washington instrument for an EXECUTED transfer.

    Modelled on native_passthrough.csv: a directed edge between two resolved
    Native entities, never an attribute of the receiving tribe's count. A
    transfer found here would carry BOTH sides or it is not written at all.
    """
    print("\n[5] transfer ledger")
    versions = [r for r in read_csv(CLEAN / "compact_versions.csv")
                if (r.get("compact_id") or "").startswith("CMP-WA-")]
    rows, candidates = [], 0
    for v in versions:
        tp = CTEXT / (v.get("text_path") or "")
        if not tp.exists():
            continue
        t = squash(tp.read_text(encoding="utf-8", errors="replace"))
        for m in RE_EXECUTED.finditer(t):
            candidates += 1
            # Reaching here means a named party sits in a transfer agreement.
            # Both sides must resolve, and a number must be present, or the
            # row is held rather than half-written.
            print("      CANDIDATE:", clean_quote(context(t, m), 240))
    print(f"    executed-transfer candidates: {candidates}")
    print(f"    transfer rows written:        {len(rows)}")
    return rows


# ---------------------------------------------------------------------------
# STAGE 7 - codebook. VARIABLES ONLY.
# ---------------------------------------------------------------------------
CODEBOOK = [
    ("07e_wa_machine_allocations", "allocation_id", "text", "code",
     "Cedar identifier for one tribe-period allocation record."),
    ("07e_wa_machine_allocations", "tribe_id", "text", "code",
     "Cedar entity spine identifier of the tribe holding the allocation."),
    ("07e_wa_machine_allocations", "tribe_name", "text", "name",
     "Spine canonical name of the tribe holding the allocation."),
    ("07e_wa_machine_allocations", "base_allocation", "integer", "devices",
     "Per-tribe entitlement stated in the instrument, in player terminals "
     "unless compact_or_appendix_cite names another device class."),
    ("07e_wa_machine_allocations", "additional_allocated", "integer", "devices",
     "Further entitlement the same instrument grants on a stated condition; "
     "0 where the instrument grants none."),
    ("07e_wa_machine_allocations", "total_authorized", "integer", "devices",
     "base_allocation plus additional_allocated. The tribe's own entitlement, "
     "not the number of machines it may operate and not the number it does."),
    ("07e_wa_machine_allocations", "effective_start", "text", "YYYY-MM-DD",
     "Date the instrument stating this entitlement took effect, on Secretarial "
     "approval published in the Federal Register."),
    ("07e_wa_machine_allocations", "effective_end", "text", "YYYY-MM-DD",
     "Day before the next instrument replaced this entitlement; empty where "
     "the entitlement is the tribe's current one."),
    ("07e_wa_machine_allocations", "measurement_type", "text", "code",
     "AUTHORIZED_MAXIMUM on every row. A held allocation is an entitlement, "
     "never an operating count, and never promotes to one."),
    ("07e_wa_machine_allocations", "compact_or_appendix_cite", "text", "citation",
     "Appendix and section stating the entitlement, the device unit, the "
     "Cedar version identifier, and any later instrument that restated it."),
    ("07e_wa_machine_allocations", "source_url", "text", "url",
     "URL of the compact or amendment PDF this entitlement was read from."),
    ("07e_wa_machine_allocations", "source_quote", "text", "text",
     "Verbatim instrument text stating the entitlement."),
    ("07e_wa_machine_allocations", "fetched_date", "text", "YYYY-MM-DD",
     "Date the source document was retrieved."),
    ("07e_wa_machine_allocations", "tier", "text", "code",
     "Cedar confidence tier. A publishes; B is internal only."),
    ("07e_wa_machine_allocations", "confidence", "text", "code",
     "instrument_stated where the instrument states the figure outright; "
     "instrument_stated_conditional where it states it subject to a review."),
    ("07e_wa_machine_allocations", "built_date", "text", "YYYY-MM-DD",
     "Date this record was built."),

    ("07e_wa_machine_transfers", "transfer_id", "text", "code",
     "Cedar identifier for one transfer of machine rights between tribes."),
    ("07e_wa_machine_transfers", "from_tribe_id", "text", "code",
     "Spine identifier of the transferring tribe, which surrenders the right "
     "to operate the terminals for the term."),
    ("07e_wa_machine_transfers", "from_tribe_name", "text", "name",
     "Spine canonical name of the transferring tribe."),
    ("07e_wa_machine_transfers", "to_tribe_id", "text", "code",
     "Spine identifier of the receiving tribe, which gains the right to "
     "operate the terminals for the term."),
    ("07e_wa_machine_transfers", "to_tribe_name", "text", "name",
     "Spine canonical name of the receiving tribe."),
    ("07e_wa_machine_transfers", "n_terminals", "integer", "devices",
     "Number of machine rights transferred, as stated in the agreement."),
    ("07e_wa_machine_transfers", "agreement_date", "text", "YYYY-MM-DD",
     "Date the transfer agreement was executed."),
    ("07e_wa_machine_transfers", "effective_start", "text", "YYYY-MM-DD",
     "First date of the transfer term."),
    ("07e_wa_machine_transfers", "effective_end", "text", "YYYY-MM-DD",
     "Last date of the transfer term."),
    ("07e_wa_machine_transfers", "consideration_disclosed", "integer", "0/1",
     "1 where the retrieved document states what was paid; 0 where it does "
     "not. Washington's Appendix D form places price in a separate agreement "
     "that is not filed with the State."),
    ("07e_wa_machine_transfers", "consideration_amount", "number", "usd",
     "Amount paid, only where consideration_disclosed is 1."),
    ("07e_wa_machine_transfers", "agreement_cite", "text", "citation",
     "Instrument and section the transfer was read from."),
    ("07e_wa_machine_transfers", "source_url", "text", "url",
     "URL of the document recording the transfer."),
    ("07e_wa_machine_transfers", "source_quote", "text", "text",
     "Verbatim text recording the transfer."),
    ("07e_wa_machine_transfers", "fetched_date", "text", "YYYY-MM-DD",
     "Date the source document was retrieved."),
    ("07e_wa_machine_transfers", "tier", "text", "code",
     "Cedar confidence tier. A publishes; B is internal only."),
    ("07e_wa_machine_transfers", "confidence", "text", "code",
     "How the transfer was established."),
    ("07e_wa_machine_transfers", "built_date", "text", "YYYY-MM-DD",
     "Date this record was built."),
]


def stage_codebook(alloc, transfers):
    print("\n[6] codebook")
    p = CLEAN / "codebook_master.csv"
    # Re-read immediately before writing and back up first: several agents
    # append to this file in the same session and a stale read silently drops
    # whichever one wrote last.
    if p.exists():
        bak = p.with_suffix(f".csv.bak_{TODAY}_pre104")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
    cb = read_csv(p)
    fields = list(cb[0].keys()) if cb else [
        "dataset", "variable", "type", "units", "pct_filled", "n_rows",
        "published", "access_tier", "description", "generated"]
    have = {(r["dataset"], r["variable"]) for r in cb}
    counts = {"07e_wa_machine_allocations": (alloc, len(alloc)),
              "07e_wa_machine_transfers": (transfers, len(transfers))}
    added = 0
    for ds, var, typ, units, desc in CODEBOOK:
        key = ("07_gaming", var) if False else (ds, var)
        if key in have:
            continue
        rows_, n = counts[ds]
        filled = (sum(1 for r in rows_ if str(r.get(var, "")).strip()) / n * 100
                  if n else 0.0)
        cb.append({"dataset": ds, "variable": var, "type": typ, "units": units,
                   "pct_filled": f"{filled:.1f}", "n_rows": n, "published": "1",
                   "access_tier": "public", "description": desc,
                   "generated": TODAY})
        added += 1
    bad = [r for r in cb if r.get("published") == "1" and not r.get("description")]
    write_csv(p, cb, fields)
    print(f"    added {added} variable rows; undocumented public now {len(bad)}")
    if bad:
        for r in bad:
            print(f"      PRE-EXISTING (not this build): {r['dataset']}."
                  f"{r['variable']}")
    return added


# ---------------------------------------------------------------------------
def main():
    print("=== Cedar Press 104: Washington machine allocations + transfers ===")
    stage_fetch()
    manifest = stage_manifest()
    amendments = stage_wsgc_amendments()
    operators, claim, shown, loc_text = stage_casino_operators()
    found, rules, versions = stage_instruments()

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    print(f"\n    spine entities: {len(spine):,}")
    alloc, unresolved = stage_periods(found, spine)
    transfers = stage_transfers(spine)

    ALLOC_FIELDS = ["allocation_id", "tribe_id", "tribe_name", "base_allocation",
                    "additional_allocated", "total_authorized",
                    "effective_start", "effective_end", "measurement_type",
                    "compact_or_appendix_cite", "source_url", "source_quote",
                    "fetched_date", "tier", "confidence", "built_date"]
    TRANS_FIELDS = ["transfer_id", "from_tribe_id", "from_tribe_name",
                    "to_tribe_id", "to_tribe_name", "n_terminals",
                    "agreement_date", "effective_start", "effective_end",
                    "consideration_disclosed", "consideration_amount",
                    "agreement_cite", "source_url", "source_quote",
                    "fetched_date", "tier", "confidence", "built_date"]

    # INVARIANT: every allocation row is an AUTHORIZED_MAXIMUM and stays one.
    assert all(r["measurement_type"] == AUTH for r in alloc)
    assert all(int(r["base_allocation"]) + int(r["additional_allocated"])
               == int(r["total_authorized"]) for r in alloc)

    print("\n[7] write")
    write_csv(CLEAN / "wa_machine_allocations.csv", alloc, ALLOC_FIELDS)
    write_csv(CLEAN / "wa_machine_transfers.csv", transfers, TRANS_FIELDS)
    write_csv(REVIEW / f"wa_allocation_unresolved_{TODAY}.csv",
              [dict(tribe_name_as_published=u["tribe_name_as_published"],
                    reason=u["reason"], version_id=u["version_id"],
                    instrument=u["instrument"], total_authorized=u["total"],
                    source_url=u["source_url"], source_quote=u["quote"],
                    tier=Tier.B.value, built_date=TODAY)
               for u in unresolved],
              ["tribe_name_as_published", "reason", "version_id", "instrument",
               "total_authorized", "source_url", "source_quote", "tier",
               "built_date"])
    stage_codebook(alloc, transfers)

    # ---- summary the build log and the report are written from -------------
    tribes = {r["tribe_id"]: r["tribe_name"] for r in alloc}
    current_pt = [r for r in alloc
                  if not r["effective_end"] and r["_unit"] == "player_terminals"]
    cur_by_tribe = {r["tribe_id"]: r for r in current_pt}

    # WSGC's own casino filter spells Quinault "Quinalt". A published typo is a
    # fact about the source, not a licence to fail the join, so the match falls
    # back to a shared 5-character prefix - enough for Quinalt/Quinault and far
    # too little to confuse any two Washington tribes with each other.
    op_norm = {norm(o) for o in operators}
    typos = []

    def operates(tribe_name):
        n_ = norm(tribe_name)
        for o in op_norm:
            if n_ == o or n_ in o or o in n_:
                return True
        for o in op_norm:
            if len(o) >= 5 and len(n_) >= 5 and o[:5] == n_[:5]:
                typos.append((tribe_name, o))
                return True
        return False

    no_casino = sorted(n for n in tribes.values() if not operates(n))
    stat = {
        "built_date": TODAY,
        "wa_compact_versions": len(versions),
        "allocation_clauses_found": len(found),
        "allocation_rows": len(alloc),
        "tribes_with_an_allocation": len(tribes),
        "unresolved": len(unresolved),
        "transfer_rows": len(transfers),
        "wsgc_operating_tribes": len(operators),
        "wsgc_claim_29_tribes_23_operate": claim,
        "wsgc_results_shown": shown,
        "tribes_with_allocation_no_wsgc_casino": no_casino,
        "wsgc_name_typos_bridged": typos,
        # Player terminals only. Colville's Appendix Colville entitlement is
        # denominated in Electronic Gaming Devices and adding it to this total
        # would sum two device classes into one number.
        "current_total_authorized_statewide_player_terminals": sum(
            int(r["total_authorized"]) for r in cur_by_tribe.values()),
        "current_by_value": Counter(
            int(r["total_authorized"]) for r in cur_by_tribe.values()),
        "non_player_terminal_series": [
            (r["tribe_name"], r["_unit"], r["total_authorized"],
             r["effective_start"]) for r in alloc
            if r["_unit"] != "player_terminals"],
        "rule_clause_counts": Counter(r["rule"] for r in rules),
        "raw_files": len(manifest),
        "wsgc_dated_instruments": len(amendments),
    }
    (CEDAR / "logs" / f"wa_allocations_summary_{TODAY}.json").write_text(
        json.dumps({k: (dict(v) if isinstance(v, Counter) else v)
                    for k, v in stat.items()}, indent=1, default=str))

    print("\n=== SUMMARY ===")
    for k, v in stat.items():
        print(f"  {k}: {v}")

    # rule quotes, for the build log
    seen = set()
    rq = []
    for r in rules:
        if r["rule"] in seen:
            continue
        seen.add(r["rule"])
        rq.append(r)
    (CEDAR / "logs" / f"wa_rule_quotes_{TODAY}.json").write_text(
        json.dumps(rq, indent=1))
    return stat


if __name__ == "__main__":
    main()
